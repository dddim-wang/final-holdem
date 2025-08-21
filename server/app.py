import os
import uuid
import json
import sqlite3
from datetime import timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)

# --- Setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-jwt")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)
CORS(app, supports_credentials=True)
sio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
jwt = JWTManager(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

# --- DB helpers ---
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

with db() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()

# --- Card & hand evaluation ---
RANKS = "23456789TJQKA"
SUITS = "SHDC"  # Spades, Hearts, Diamonds, Clubs

@dataclass
class Player:
    sid: str
    name: str
    in_hand: bool = True
    cards: List[str] = field(default_factory=list)
    raises: int = 0  # cumulative count of bets (4 or 8) made
    action_submitted: bool = False
    pot: int = 0

@dataclass
class Game:
    game_id: str
    host_sid: Optional[str] = None
    players: Dict[str, Player] = field(default_factory=dict)  # sid -> Player
    deck: List[str] = field(default_factory=list)
    board: List[str] = field(default_factory=list)
    stage: str = "lobby"  # lobby, preflop, flop2, flop3, turn, river, showdown
    pot: int = 0
    round_actions: Dict[str, str] = field(default_factory=dict)  # sid -> action
    someone_raised: bool = False
    current_bet: int = 0  # highest bet in current round
    raise_made: bool = False  # whether someone has already raised in this round
    max_players: int = 15

    def reset_deck(self):
        self.deck = [r + s for r in RANKS for s in SUITS]
        import random
        random.shuffle(self.deck)

    def deal_to_all(self):
        for p in list(self.players.values()):
            if p.in_hand:
                p.cards = [self.deck.pop(), self.deck.pop()]

    def active_sids(self) -> List[str]:
        return [p.sid for p in self.players.values() if p.in_hand]

    def everyone_acted(self) -> bool:
        for sid in self.active_sids():
            p = self.players[sid]
            if p.name.startswith("Host-"):
                continue
            # Check if player needs to call the current bet
            if p.in_hand and p.pot < self.current_bet:
                # Player hasn't called the current bet yet
                if not p.action_submitted:
                    return False
            elif p.in_hand and not p.action_submitted:
                # Player is in hand but hasn't acted yet
                return False
        return True

# All live games by id
GAMES: Dict[str, Game] = {}

# --- Hand evaluator helpers ---
from itertools import combinations

RANK_TO_VAL = {r: i for i, r in enumerate(RANKS, start=2)}

HAND_ORDER = {
    "high": 0,
    "pair": 1,
    "two_pair": 2,
    "three": 3,
    "straight": 4,
    "flush": 5,
    "full_house": 6,
    "four": 7,
    "straight_flush": 8,
}

def card_to_tuple(c: str) -> Tuple[int, str]:
    return (RANK_TO_VAL[c[0]], c[1])

def is_straight(vals: List[int]) -> Optional[int]:
    # vals should already be sorted descending
    uniq = sorted(set(vals), reverse=True)
    
    # Check for wheel straight (A-2-3-4-5) - lowest straight
    if {14, 2, 3, 4, 5}.issubset(set(vals)):
        return 5  # Return 5 as the high card for wheel straight
    
    # Check for regular straights (5 cards in sequence)
    for i in range(len(uniq) - 4):
        window = uniq[i:i+5]
        if window[0] - window[4] == 4:  # Consecutive values
            return window[0]  # Return the high card of the straight
    
    return None

def classify_5(cards5: List[str]):
    vals = sorted([card_to_tuple(c)[0] for c in cards5], reverse=True)
    suits = [c[1] for c in cards5]
    ranks = [c[0] for c in cards5]
    is_flush = len(set(suits)) == 1
    top_straight = is_straight(vals)

    # counts
    from collections import Counter
    ctr = Counter(vals)
    counts = sorted(ctr.items(), key=lambda x: (-x[1], -x[0]))  # by count desc, then rank desc

    if is_flush and top_straight:
        return (HAND_ORDER["straight_flush"], top_straight, vals)
    if counts[0][1] == 4:
        # four of a kind
        quad = counts[0][0]
        kicker = max([v for v in vals if v != quad])
        return (HAND_ORDER["four"], quad, [kicker])
    if counts[0][1] == 3 and counts[1][1] == 2:
        # full house
        trips = counts[0][0]
        pair = counts[1][0]
        return (HAND_ORDER["full_house"], trips, [pair])
    if is_flush:
        return (HAND_ORDER["flush"], vals)
    if top_straight:
        return (HAND_ORDER["straight"], top_straight)
    if counts[0][1] == 3:
        trips = counts[0][0]
        kickers = sorted([v for v in vals if v != trips], reverse=True)[:2]
        return (HAND_ORDER["three"], trips, kickers)
    if counts[0][1] == 2 and counts[1][1] == 2:
        # two pair - ensure high pair is first, low pair is second, then kicker
        high_pair = max(counts[0][0], counts[1][0])
        low_pair = min(counts[0][0], counts[1][0])
        kicker = max([v for v in vals if v != high_pair and v != low_pair])
        return (HAND_ORDER["two_pair"], high_pair, low_pair, kicker)
    if counts[0][1] == 2:
        pair = counts[0][0]
        kickers = sorted([v for v in vals if v != pair], reverse=True)[:3]
        return (HAND_ORDER["pair"], pair, kickers)
    return (HAND_ORDER["high"], vals)

HAND_NAME = {
    HAND_ORDER["high"]: "High Card",
    HAND_ORDER["pair"]: "One Pair",
    HAND_ORDER["two_pair"]: "Two Pair",
    HAND_ORDER["three"]: "Three of a Kind",
    HAND_ORDER["straight"]: "Straight",
    HAND_ORDER["flush"]: "Flush",
    HAND_ORDER["full_house"]: "Full House",
    HAND_ORDER["four"]: "Four of a Kind",
    HAND_ORDER["straight_flush"]: "Straight Flush",
}

def best_hand(hole: List[str], board: List[str]):
    best = None
    best5 = None
    print(f"DEBUG: Evaluating hand for hole cards {hole} and board {board}")
    for combo in combinations(hole + board, 5):
        score = classify_5(list(combo))
        if (best is None) or (score > best):
            best = score
            best5 = list(combo)
            print(f"DEBUG: New best hand: {combo} with score {score}")
    hand_name = HAND_NAME[best[0]]
    print(f"DEBUG: Final best hand: {best5} with name {hand_name}")
    return best, best5, hand_name

def best_board_hand(board: List[str]):
    """Evaluate the best possible hand from just the board cards"""
    if len(board) < 5:
        return None, None, "Incomplete Board"
    
    best = None
    best5 = None
    for combo in combinations(board, 5):
        score = classify_5(list(combo))
        if (best is None) or (score > best):
            best = score
            best5 = list(combo)
    
    if best:
        hand_name = HAND_NAME[best[0]]
        return best, best5, hand_name
    return None, None, "No Hand"

# --- REST: auth & comments & rankings ---
@app.post("/api/register")
def register():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    # Validate username length
    if len(username) > 20:
        return jsonify({"error": "Username must be 20 characters or less"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    pw_hash = generate_password_hash(password)
    try:
        with db() as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "username already exists"}), 409
    # Auto-login after registration by returning access token
    token = create_access_token(identity=username)
    return jsonify({"access_token": token, "username": username})

@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    # Validate username length
    if len(username) > 20:
        return jsonify({"error": "Username must be 20 characters or less"}), 400
    
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401
    token = create_access_token(identity=username)
    return jsonify({"access_token": token, "username": username})

@app.get("/api/comments")
def get_comments():
    game_id = request.args.get("game_id", "")
    with db() as conn:
        rows = conn.execute(
            "SELECT username, content, created_at FROM comments WHERE game_id=? ORDER BY id DESC LIMIT 50",
            (game_id,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/comments")
@jwt_required()
def post_comment():
    data = request.get_json(force=True)
    content = data.get("content", "").strip()
    game_id = data.get("game_id", "").strip()
    username = get_jwt_identity()
    if not content or not game_id:
        return jsonify({"error": "content and game_id required"}), 400
    with db() as conn:
        conn.execute("INSERT INTO comments (game_id, username, content) VALUES (?, ?, ?)", (game_id, username, content))
        conn.commit()
    # Broadcast to room ticker
    sio.emit("new_comment", {"username": username, "content": content}, to=game_id)
    return jsonify({"ok": True})

@app.get("/api/hand-rankings")
def hand_rankings():
    ranks = [
        "Straight Flush",
        "Four of a Kind",
        "Full House",
        "Flush",
        "Straight",
        "Three of a Kind",
        "Two Pair",
        "One Pair",
        "High Card",
    ]
    return jsonify(ranks)

# --- Socket.IO events ---
@sio.on("connect")
def on_connect():
    emit("connected", {"sid": request.sid})

@sio.on("disconnect")
def on_disconnect():
    sid = request.sid
    # Remove from any game
    for g in list(GAMES.values()):
        if sid in g.players:
            name = g.players[sid].name
            del g.players[sid]
            # If host disconnected, clear host_sid
            if sid == g.host_sid:
                g.host_sid = None
            # Count only non-host players for lobby updates
            non_host_count = len([p for p in g.players.values() if not p.name.startswith("Host-")])
            sio.emit("lobby_update", {"count": non_host_count, "max": g.max_players}, to=g.game_id)
            sio.emit("system", {"msg": f"{name} left."}, to=g.game_id)
            # Emit updated state to all players including host
            sio.emit("state", serialize_game(g), to=g.game_id)
            break

@sio.on("host_create_game")
def host_create_game(data):
    game_id = uuid.uuid4().hex[:6].upper()
    g = Game(game_id=game_id, host_sid=request.sid)
    GAMES[game_id] = g
    join_room(game_id)
    emit("game_created", {"gameId": game_id})

@sio.on("join_game")
def join_game(data):
    game_id = (data or {}).get("gameId")
    name = (data or {}).get("name", "Player")[:20]
    if game_id not in GAMES:
        return emit("error", {"error": "Game not found"})
    g = GAMES[game_id]
    # Count only non-host players when checking if game is full
    non_host_players = len([p for p in g.players.values() if not p.name.startswith("Host-")])
    if non_host_players >= g.max_players:
        return emit("error", {"error": "Game is full"})
    join_room(game_id)
    g.players[request.sid] = Player(sid=request.sid, name=name)
    # Count only non-host players for lobby updates
    non_host_count = len([p for p in g.players.values() if not p.name.startswith("Host-")])
    sio.emit("lobby_update", {"count": non_host_count, "max": g.max_players}, to=g.game_id)
    sio.emit("system", {"msg": f"{name} joined."}, to=game_id)
    # Emit updated state to all players including host
    sio.emit("state", serialize_game(g), to=game_id)
    emit("joined", {"gameId": game_id})

@sio.on("host_start")
def host_start(data):
    print("Host started game.")
    game_id = (data or {}).get("gameId")
    if game_id not in GAMES:
        return emit("error", {"error": "Game not found"})
    g = GAMES[game_id]
    if request.sid != g.host_sid:
        return emit("error", {"error": "Only host can start"})
    # Setup deck and deal
    g.reset_deck()
    g.board = []
    g.pot = 0
    g.stage = "preflop"
    g.someone_raised = False
    g.current_bet = 0
    g.raise_made = False
    for p in g.players.values():
        p.in_hand = True
        p.action_submitted = False
        p.raises = 0
        p.pot = 0
        p.cards = []
    g.deal_to_all()
    # send private cards
    for p in g.players.values():
        sio.emit("your_cards", {"cards": p.cards}, to=p.sid)
    sio.emit("state", serialize_game(g), to=game_id)

@sio.on("player_action")
def player_action(data):
    game_id = (data or {}).get("gameId")
    action = (data or {}).get("action")  # check, bet4, bet8, call, fold, raise
    if game_id not in GAMES:
        return emit("error", {"error": "Game not found"})
    g = GAMES[game_id]
    if request.sid not in g.players:
        return emit("error", {"error": "Not in this game"})
    p = g.players[request.sid]
    if not p.in_hand:
        return
    if p.action_submitted:
        return  # one action per round

    # Check if player needs to call (they're below current bet)
    needs_to_call = p.pot < g.current_bet

    if action == "fold":
        p.in_hand = False
        p.action_submitted = True
    elif action == "check":
        if needs_to_call:
            return emit("error", {"error": "Must call or fold - cannot check"})
        p.action_submitted = True
    elif action == "call":
        if not needs_to_call:
            return emit("error", {"error": "No need to call - you can check"})
        call_amount = g.current_bet - p.pot
        p.pot += call_amount
        g.pot += call_amount
        p.action_submitted = True
    elif action == "bet4":
        # If current bet is 8, bet4 is not allowed (must call 8 or raise to 12)
        if g.current_bet == 8:
            return emit("error", {"error": "Cannot bet 4 when current bet is 8. Must call 8 or raise to 12"})
        # If someone already raised in this round, can't bet 4 anymore
        if g.raise_made:
            return emit("error", {"error": "Someone already raised in this round. You can only call or fold."})
        p.pot += 4
        g.pot += 4
        p.raises += 1
        p.action_submitted = True
        g.someone_raised = True
        old_bet = g.current_bet
        g.current_bet = max(g.current_bet, p.pot)
        print(f"Player {p.name} bet 4. Current bet now: {g.current_bet}, Player pot: {p.pot}")
        
        # If the current bet increased, reset action_submitted for all other players so they can act again
        if g.current_bet > old_bet:
            for other_p in g.players.values():
                if other_p.sid != p.sid and other_p.in_hand:
                    other_p.action_submitted = False
                    print(f"Reset action for {other_p.name} due to bet increase")
    elif action == "bet8":
        # If someone already raised in this round, can't raise again
        if g.raise_made:
            return emit("error", {"error": "Someone already raised in this round. You can only call or fold."})
        p.pot += 8
        g.pot += 8
        p.raises += 1
        p.action_submitted = True
        g.someone_raised = True
        g.raise_made = True  # Mark that a raise has been made
        old_bet = g.current_bet
        g.current_bet = max(g.current_bet, p.pot)
        # Reset action_submitted for all other players so they can act again
        for other_p in g.players.values():
            if other_p.sid != p.sid and other_p.in_hand:
                other_p.action_submitted = False
                print(f"Reset action for {other_p.name} due to bet8")
        print(f"Player {p.name} bet 8. Current bet now: {g.current_bet}, Player pot: {p.pot}")
    else:
        return emit("error", {"error": "Invalid action"})

    sio.emit("state", serialize_game(g), to=g.game_id)
    
    # Check if only one player remains in hand (early winner)
    active_players = [p for p in g.players.values() if p.in_hand and not p.name.startswith("Host-")]
    if len(active_players) == 1 and g.stage != "lobby":
        # Only one player left - they win automatically
        winner = active_players[0]
        
        # Safety check: ensure winner has valid data
        if not winner or not winner.name:
            print("ERROR: Invalid winner data in early winner scenario")
            return
            
        early_winner_data = {
            "winners": [winner.name],
            "pot": g.pot,
            "board": g.board,
            "hand_name": "Last Player Standing",
            "early_winner": True,
            "show": [
                {"name": winner.name, "cards": winner.cards, "best5": winner.cards, "score": "early_win", "hand_name": "Last Player Standing"}
            ],
        }
        g.stage = "showdown"
        sio.emit("showdown", early_winner_data, to=g.game_id)
        sio.emit("state", serialize_game(g), to=g.game_id)
        return
    
    if g.everyone_acted():
        sio.emit("round_settled", {"ok": True}, to=g.game_id)

@sio.on("host_deal_next")
def host_deal_next(data):
    print("Host dealt next cards.")
    game_id = (data or {}).get("gameId")
    print(game_id)
    if game_id not in GAMES:
        return emit("error", {"error": "Game not found"})
    g = GAMES[game_id]
    print(g)
    if request.sid != g.host_sid:
        return emit("error", {"error": "Only host can deal"})

    # Ensure all active players acted
    if not g.everyone_acted() and g.stage != "lobby":
        print("Not all players have acted.")
        return emit("error", {"error": "Wait for all players"})

    # Advance stage & reveal board
    if g.stage == "preflop":
        print("Preflop stage dealing next cards...")
        # reveal 2 (first flop)
        g.board.append(g.deck.pop())
        g.board.append(g.deck.pop())
        g.stage = "flop2"
    elif g.stage == "flop2":
        g.board.append(g.deck.pop())  # third flop card
        g.stage = "flop3"
    elif g.stage == "flop3":
        g.board.append(g.deck.pop())  # turn
        g.stage = "turn"
    elif g.stage == "turn":
        g.board.append(g.deck.pop())  # river
        g.stage = "river"
    elif g.stage == "river":
        g.stage = "showdown"
        
        # Safety check: ensure there are active players for showdown
        active_players = [p for p in g.players.values() if p.in_hand]
        if not active_players:
            print("ERROR: No active players for showdown - this should not happen!")
            # Fallback: create a default result
            fallback_result = {
                "winners": [],
                "pot": g.pot,
                "board": g.board,
                "hand_name": "No Players",
                "board_win": False,
                "error": "No active players found for showdown",
                "show": []
            }
            sio.emit("showdown", fallback_result, to=g.game_id)
            sio.emit("state", serialize_game(g), to=g.game_id)
            return
        
        winners = compute_winners(g)
        print(f"DEBUG: Sending showdown results: {winners}")
        print(f"DEBUG: Winners array type: {type(winners['winners'])}")
        print(f"DEBUG: Winners array content: {winners['winners']}")
        print(f"DEBUG: Winners array length: {len(winners['winners'])}")
        
        # Final safety check: ensure winners array is not empty
        if not winners.get('winners') and not winners.get('error'):
            print("ERROR: No winners found in showdown - this should not happen!")
            winners['error'] = 'No winners determined'
            winners['winners'] = [p.name for p in active_players]  # Fallback to all active players
        
        sio.emit("showdown", winners, to=g.game_id)
        sio.emit("state", serialize_game(g), to=g.game_id)
        return

    # Reset per-round flags for next betting round
    for p in g.players.values():
        if p.in_hand:
            p.action_submitted = False
    g.someone_raised = False
    g.current_bet = 0
    g.raise_made = False

    sio.emit("state", serialize_game(g), to=g.game_id)

@sio.on("request_state")
def request_state(data):
    game_id = (data or {}).get("gameId")
    if game_id in GAMES:
        sio.emit("state", serialize_game(GAMES[game_id]), to=request.sid)

@sio.on("host_reset_round")
def host_reset_round(data):
    game_id = (data or {}).get("gameId")
    if game_id not in GAMES:
        return emit("error", {"error": "Game not found"})
    g = GAMES[game_id]
    if request.sid != g.host_sid:
        return emit("error", {"error": "Only host can reset"})
    # Reset to lobby stage - host must start again
    g.board = []
    g.pot = 0
    g.stage = "lobby"  # Changed from "preflop" to "lobby"
    g.someone_raised = False
    g.current_bet = 0
    g.raise_made = False
    g.reset_deck()
    for p in g.players.values():
        p.in_hand = False  # Changed from True to False
        p.action_submitted = False
        p.raises = 0
        p.pot = 0
        p.cards = []  # Clear all cards
    # Don't deal cards - wait for host to start
    sio.emit("state", serialize_game(g), to=g.game_id)

# --- helpers ---
def compute_winners(g: Game):
    """Compute winners following proper Texas Hold'em rules"""
    # Determine active players (those who did not fold before showdown)
    contenders = [p for p in g.players.values() if p.in_hand]
    if not contenders:
        # This should never happen in a valid game, but if it does, return error
        print("ERROR: No contenders found - this should not happen!")
        return {"winners": [], "hand": None, "error": "No active players found"}
    
    print(f"DEBUG: Computing winners for {len(contenders)} contenders")
    
    # First, check what the best possible hand from the board is
    board_score, board_best5, board_hand_name = best_board_hand(g.board)
    print(f"DEBUG: Best board hand: {board_hand_name} with score {board_score}")
    
    # Compute best hands for each player
    scored = []
    for p in contenders:
        score, five, name = best_hand(p.cards, g.board)
        scored.append((score, p, name, five))
        print(f"DEBUG: Player {p.name} has cards {p.cards}, board is {g.board}")
        print(f"DEBUG: Best hand: {name}, score: {score}")
    
    # Sort by score (highest first) - this handles hand type ranking
    scored.sort(reverse=True, key=lambda t: t[0])
    top_score = scored[0][0]
    
    print(f"DEBUG: Top score is {top_score}")
    
    # Check if the board itself contains the best possible hand
    if board_score and board_score >= top_score:
        # Board contains the best hand - all active players split the pot
        if board_score == top_score:
            # Players tied with the board - this is a board win scenario
            print(f"DEBUG: Board contains best hand - all players split the pot!")
            return {
                "winners": [p.name for p in contenders],  # ✅ ALL active players win and split the pot
                "pot": g.pot,
                "board": g.board,
                "hand_name": board_hand_name,
                "board_win": True,  # Mark this as a board win
                "show": [
                    {"name": s[1].name, "cards": s[1].cards, "best5": s[3], "score": str(s[0]), "hand_name": s[2]} 
                    for s in scored
                ],
            }
        else:
            # Board is better than any player hand - all active players split the pot
            print(f"DEBUG: Board contains best hand - all players split the pot!")
            return {
                "winners": [p.name for p in contenders],  # ✅ ALL active players win and split the pot
                "pot": g.pot,
                "board": g.board,
                "hand_name": board_hand_name,
                "board_win": True,  # Mark this as a board win
                "show": [
                    {"name": s[1].name, "cards": s[1].cards, "best5": s[3], "score": str(s[0]), "hand_name": s[2]} 
                    for s in scored
                ],
            }
    
    # Find all players with the same top score (potential ties)
    top_players = [s for s in scored if s[0] == top_score]
    
    if len(top_players) == 1:
        # Single winner - no tie
        winner = top_players[0]
        winners = [winner[1].name]
        print(f"DEBUG: Single winner: {winners[0]} with {winner[2]}")
    else:
        # Multiple players with same hand type - need to break tie
        print(f"DEBUG: {len(top_players)} players tied with same hand type")
        winners = break_tie(top_players, g.board)
        print(f"DEBUG: After tie-break, winners: {winners}")
    
    # Ensure we always have at least one winner
    if not winners:
        print("ERROR: No winners found after tie-breaking - this should not happen!")
        # Fallback: all top players split the pot
        winners = [p[1].name for p in top_players]
        print(f"DEBUG: Fallback to split pot between: {winners}")
    
    return {
        "winners": winners,
        "pot": g.pot,
        "board": g.board,
        "hand_name": HAND_NAME[top_score[0]],
        "board_win": False,  # Not a board win
        "show": [
            {"name": s[1].name, "cards": s[1].cards, "best5": s[3], "score": str(s[0]), "hand_name": s[2]} 
            for s in scored
        ],
    }

def break_tie(tied_players, board):
    """Break ties between players with the same hand type"""
    if not tied_players:
        return []
    
    # Get the hand type and scores
    hand_type = tied_players[0][0][0]
    print(f"DEBUG: Breaking tie for hand type: {HAND_NAME[hand_type]}")
    
    if hand_type == HAND_ORDER["straight_flush"]:
        return break_straight_tie(tied_players)
    elif hand_type == HAND_ORDER["four"]:
        return break_four_tie(tied_players)
    elif hand_type == HAND_ORDER["full_house"]:
        return break_full_house_tie(tied_players)
    elif hand_type == HAND_ORDER["flush"]:
        return break_flush_tie(tied_players)
    elif hand_type == HAND_ORDER["straight"]:
        return break_straight_tie(tied_players)
    elif hand_type == HAND_ORDER["three"]:
        return break_three_tie(tied_players)
    elif hand_type == HAND_ORDER["two_pair"]:
        return break_two_pair_tie(tied_players)
    elif hand_type == HAND_ORDER["pair"]:
        return break_pair_tie(tied_players)
    else:  # high card
        return break_high_card_tie(tied_players)

def break_straight_tie(tied_players):
    """Break ties for straights and straight flushes"""
    # For straights, compare the high card of the straight
    high_cards = [(p[0][1], p[1].name) for p in tied_players]
    high_cards.sort(reverse=True)
    highest = high_cards[0][0]
    winners = [name for high, name in high_cards if high == highest]
    return winners

def break_four_tie(tied_players):
    """Break ties for four of a kind"""
    # Compare the four of a kind rank, then kicker
    four_ranks = [(p[0][1], p[0][2][0], p[1].name) for p in tied_players]
    four_ranks.sort(reverse=True)
    highest_four = four_ranks[0][0]
    highest_kicker = four_ranks[0][1]
    
    # Find players with highest four of a kind
    candidates = [(four, kicker, name) for four, kicker, name in four_ranks if four == highest_four]
    
    if len(candidates) == 1:
        return [candidates[0][2]]
    
    # Break tie with kicker
    highest_kicker = max(kicker for four, kicker, name in candidates)
    winners = [name for four, kicker, name in candidates if kicker == highest_kicker]
    return winners

def break_full_house_tie(tied_players):
    """Break ties for full house"""
    # Compare trips rank, then pair rank
    trip_ranks = [(p[0][1], p[0][2][0], p[1].name) for p in tied_players]
    trip_ranks.sort(reverse=True)
    highest_trips = trip_ranks[0][0]
    highest_pair = trip_ranks[0][1]
    
    # Find players with highest trips
    candidates = [(trips, pair, name) for trips, pair, name in trip_ranks if trips == highest_trips]
    
    if len(candidates) == 1:
        return [candidates[0][2]]
    
    # Break tie with pair rank
    highest_pair = max(pair for trips, pair, name in candidates)
    winners = [name for trips, pair, name in candidates if pair == highest_pair]
    return winners

def break_flush_tie(tied_players):
    """Break ties for flush"""
    # Compare all 5 cards in descending order
    return break_high_card_tie(tied_players)

def break_three_tie(tied_players):
    """Break ties for three of a kind"""
    # Compare trips rank, then kickers
    trip_ranks = [(p[0][1], p[0][2], p[1].name) for p in tied_players]
    trip_ranks.sort(reverse=True)
    highest_trips = trip_ranks[0][0]
    
    # Find players with highest trips
    candidates = [(trips, kickers, name) for trips, kickers, name in trip_ranks if trips == highest_trips]
    
    if len(candidates) == 1:
        return [candidates[0][2]]
    
    # Break tie with kickers
    return break_kicker_tie(candidates)

def break_two_pair_tie(tied_players):
    """Break ties for two pair"""
    # Compare high pair, then low pair, then kicker
    pair_ranks = [(p[0][1], p[0][2], p[0][3], p[1].name) for p in tied_players]
    pair_ranks.sort(reverse=True)
    highest_high = pair_ranks[0][0]
    highest_low = pair_ranks[0][1]
    highest_kicker = pair_ranks[0][2]
    
    # Find players with highest high pair
    candidates = [(high, low, kicker, name) for high, low, kicker, name in pair_ranks if high == highest_high]
    
    if len(candidates) == 1:
        return [candidates[0][3]]
    
    # Break tie with low pair
    highest_low = max(low for high, low, kicker, name in candidates)
    candidates = [(high, low, kicker, name) for high, low, kicker, name in candidates if low == highest_low]
    
    if len(candidates) == 1:
        return [candidates[0][3]]
    
    # Break tie with kicker
    highest_kicker = max(kicker for high, low, kicker, name in candidates)
    winners = [name for high, low, kicker, name in candidates if kicker == highest_kicker]
    return winners

def break_pair_tie(tied_players):
    """Break ties for one pair"""
    # Compare pair rank, then kickers
    pair_ranks = [(p[0][1], p[0][2], p[1].name) for p in tied_players]
    pair_ranks.sort(reverse=True)
    highest_pair = pair_ranks[0][0]
    
    # Find players with highest pair
    candidates = [(pair, kickers, name) for pair, kickers, name in pair_ranks if pair == highest_pair]
    
    if len(candidates) == 1:
        return [candidates[0][2]]
    
    # Break tie with kickers
    return break_kicker_tie(candidates)

def break_high_card_tie(tied_players):
    """Break ties for high card"""
    # Compare all 5 cards in descending order
    return break_kicker_tie([(p[0][1], p[1].name) for p in tied_players])

def break_kicker_tie(candidates):
    """Break ties using kicker cards"""
    if not candidates:
        return []
    
    # Get the kicker values (could be single value or list)
    kicker_data = []
    for candidate in candidates:
        if len(candidate) == 2:  # (kickers, name)
            kickers = candidate[0]
        else:  # (main, kickers, name)
            kickers = candidate[1]
        
        if isinstance(kickers, list):
            kicker_data.append((kickers, candidate[-1]))  # (kickers, name)
        else:
            kicker_data.append(([kickers], candidate[-1]))  # (kickers, name)
    
    # Compare kickers one by one
    max_kickers = max(len(kickers) for kickers, name in kicker_data)
    
    for i in range(max_kickers):
        # Get the i-th kicker for each player (or 0 if they don't have that many)
        current_kickers = []
        for kickers, name in kicker_data:
            if i < len(kickers):
                current_kickers.append((kickers[i], name))
            else:
                current_kickers.append((0, name))
        
        # Find highest kicker at this position
        current_kickers.sort(reverse=True)
        highest = current_kickers[0][0]
        
        # Keep only players with the highest kicker at this position
        kicker_data = [(kickers, name) for kicker, name in current_kickers if kicker == highest]
        
        if len(kicker_data) == 1:
            return [kicker_data[0][1]]
    
    # If we get here, all kickers are equal - it's a true tie
    return [name for kickers, name in kicker_data]

def serialize_game(g: Game):
    result = {
        "gameId": g.game_id,
        "stage": g.stage,
        "board": g.board,
        "pot": g.pot,
        "someoneRaised": g.someone_raised,
        "currentBet": g.current_bet,
        "raiseMade": g.raise_made,
        "players": [
            {
                "name": p.name, 
                "inHand": p.in_hand, 
                "raises": p.raises, 
                "acted": p.action_submitted, 
                "pot": p.pot,
                "needsToCall": p.in_hand and p.pot < g.current_bet and not p.action_submitted
            }
            for p in g.players.values()
        ],
        "count": len([p for p in g.players.values() if not p.name.startswith("Host-")]),
        "max": g.max_players,
    }
    print(f"Serialized game - Current bet: {g.current_bet}, Raise made: {g.raise_made}, Players: {[(p.name, p.pot, p.in_hand and p.pot < g.current_bet and not p.action_submitted) for p in g.players.values()]}")
    return result

if __name__ == "__main__":
    # Run with eventlet for WebSockets
    import eventlet
    import eventlet.wsgi
    print("Starting server on http://localhost:5000")
    sio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True, debug=True)


    