import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import hashlib
import chess
import random
import string
import time
import json

st.set_page_config(page_title="AURELIA CHESS // Online Arena", page_icon="♛", layout="wide")

# ==========================================
# 1. Obsidian & Gold Studio Design System
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0b0d11;
        color: #f1f5f9;
    }
    .stApp {
        background: radial-gradient(circle at top right, #161b26 0%, #0b0d11 55%);
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        max-width: 1320px;
    }

    /* Hide default Streamlit header/footer clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Brand Header */
    .brand-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #f8fafc 0%, #d4af37 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .brand-sub {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(20, 24, 33, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        margin-bottom: 12px;
    }

    /* Profile Stat Pill */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-top: 10px;
    }
    .stat-box {
        background: #11151d;
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
    .stat-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.25rem;
        font-weight: 700;
        color: #d4af37;
    }
    .stat-lbl {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #64748b;
    }

    /* Arena Player Bars */
    .arena-bar {
        background: #131720;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 12px;
        padding: 10px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        transition: all 0.2s ease;
    }
    .arena-bar.active {
        border-color: #d4af37;
        background: linear-gradient(90deg, rgba(212, 175, 55, 0.12) 0%, #131720 100%);
        box-shadow: 0 0 18px rgba(212, 175, 55, 0.15);
    }
    .player-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .elo-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        background: rgba(212, 175, 55, 0.15);
        color: #f3d060;
        border: 1px solid rgba(212, 175, 55, 0.3);
        padding: 2px 7px;
        border-radius: 6px;
    }
    .clock-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.45rem;
        font-weight: 700;
        padding: 5px 14px;
        border-radius: 8px;
        background: #0b0d11;
        color: #64748b;
        border: 1px solid rgba(255,255,255,0.06);
    }
    .clock-pill.running {
        background: #f8fafc;
        color: #0b0d11;
        border-color: #ffffff;
    }
    .clock-pill.danger {
        background: #ef4444;
        color: #ffffff;
        border-color: #f87171;
    }
    .cap-strip {
        font-size: 1.05rem;
        color: #94a3b8;
        min-height: 22px;
        margin-top: 2px;
    }
    .mat-plus {
        background: #1e293b;
        color: #34d399;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        padding: 1px 6px;
        border-radius: 4px;
        margin-left: 6px;
    }

    /* Bot Roster Cards */
    .bot-badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Bot Roster & Chess AI Engine
# ==========================================
BOT_PROFILES = {
    "Martin (400 ELO)": {
        "name": "🤖 Martin",
        "elo": 400,
        "depth": 1,
        "blunder_rate": 0.65,
        "desc": "Friendly beginner. Hangs pieces frequently and plays mostly on instinct."
    },
    "Nova (800 ELO)": {
        "name": "🤖 Nova",
        "elo": 800,
        "depth": 1,
        "blunder_rate": 0.30,
        "desc": "Casual club rookie. Spots basic captures but misses 2-move tactics."
    },
    "Vex (1200 ELO)": {
        "name": "🤖 Vex",
        "elo": 1200,
        "depth": 2,
        "blunder_rate": 0.12,
        "desc": "Intermediate tactician. Develops pieces cleanly and punishes obvious blunders."
    },
    "Kira (1500 ELO)": {
        "name": "🤖 Kira",
        "elo": 1500,
        "depth": 2,
        "blunder_rate": 0.0,
        "desc": "Tournament contender. Solid positional structure and sharp tactical vision."
    },
    "Magnus-Lite (1800 ELO)": {
        "name": "🤖 Magnus-Lite",
        "elo": 1800,
        "depth": 3,
        "blunder_rate": 0.0,
        "desc": "Advanced engine. Calculates deep combinations and squeezes endgames."
    },
    "Stock-Zero (2000 ELO)": {
        "name": "🤖 Stock-Zero",
        "elo": 2000,
        "depth": 3,
        "blunder_rate": 0.0,
        "desc": "Master-level predator. Ruthless alpha-beta search with aggressive center control."
    }
}

# Piece-Square Tables (White perspective)
PST_PAWN = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 10,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0
]
PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]
PST_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]
PST_ROOK = [
    0,  0,  0,  0,  0,  0,  0,  0,
    5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    0,  0,  0,  5,  5,  0,  0,  0
]
PST_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]
PST_KING = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20
]

PST_MAP = {
    chess.PAWN: (100, PST_PAWN),
    chess.KNIGHT: (320, PST_KNIGHT),
    chess.BISHOP: (330, PST_BISHOP),
    chess.ROOK: (500, PST_ROOK),
    chess.QUEEN: (900, PST_QUEEN),
    chess.KING: (20000, PST_KING)
}

def evaluate_board(board, elo_level=1500):
    if board.is_checkmate():
        return -99999 if board.turn == chess.WHITE else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if not piece:
            continue
        base_val, pst = PST_MAP[piece.piece_type]
        if piece.color == chess.WHITE:
            idx = chess.square_mirror(sq)
            pos_bonus = pst[idx] if elo_level >= 1200 else 0
            score += (base_val + pos_bonus)
        else:
            pos_bonus = pst[sq] if elo_level >= 1200 else 0
            score -= (base_val + pos_bonus)

    # Extra mobility/center bonus for high-ELO bots
    if elo_level >= 1800:
        score += (10 if board.turn == chess.WHITE else -10)
    return score

def order_moves(board):
    moves = list(board.legal_moves)
    def move_priority(m):
        prio = 0
        if board.is_capture(m):
            prio += 10
        if m.promotion:
            prio += 9
        if board.gives_check(m):
            prio += 5
        return prio
    moves.sort(key=move_priority, reverse=True)
    return moves

def minimax(board, depth, alpha, beta, maximizing_white, elo_level):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board, elo_level), None

    ordered = order_moves(board)
    best_move = ordered[0]

    if maximizing_white:
        max_eval = -999999
        for move in ordered:
            board.push(move)
            ev, _ = minimax(board, depth - 1, alpha, beta, False, elo_level)
            board.pop()
            if ev > max_eval:
                max_eval = ev
                best_move = move
            alpha = max(alpha, ev)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = 999999
        for move in ordered:
            board.push(move)
            ev, _ = minimax(board, depth - 1, alpha, beta, True, elo_level)
            board.pop()
            if ev < min_eval:
                min_eval = ev
                best_move = move
            beta = min(beta, ev)
            if beta <= alpha:
                break
        return min_eval, best_move

def choose_bot_move(board, bot_key):
    profile = BOT_PROFILES[bot_key]
    legal = list(board.legal_moves)
    if not legal:
        return None
    if random.random() < profile["blunder_rate"]:
        return random.choice(legal).uci()

    maximizing = (board.turn == chess.WHITE)
    _, best_move = minimax(board, profile["depth"], -999999, 999999, maximizing, profile["elo"])
    return best_move.uci() if best_move else random.choice(legal).uci()

# ==========================================
# 3. Database Layer (Accounts, ELO & Games)
# ==========================================
DB_FILE = "aurelia_chess_v2.db"

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            elo INTEGER DEFAULT 1000,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS games (
            room_code TEXT PRIMARY KEY,
            fen TEXT NOT NULL,
            pgn_moves TEXT DEFAULT '',
            last_move_uci TEXT DEFAULT '',
            white_player TEXT,
            black_player TEXT,
            white_elo INTEGER DEFAULT 1000,
            black_elo INTEGER DEFAULT 1000,
            is_bot_game INTEGER DEFAULT 0,
            bot_key TEXT DEFAULT '',
            status TEXT DEFAULT 'waiting',
            result_reason TEXT DEFAULT '',
            elo_processed INTEGER DEFAULT 0,
            time_control INTEGER DEFAULT 600,
            increment INTEGER DEFAULT 0,
            white_time REAL DEFAULT 600.0,
            black_time REAL DEFAULT 600.0,
            last_tick REAL DEFAULT 0.0,
            draw_offer TEXT DEFAULT '',
            chat_log TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def register_account(username, password):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash, elo, wins, losses, draws) VALUES (?, ?, 1000, 0, 0, 0)",
            (username, hash_pw(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_account(username, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, elo, wins, losses, draws FROM users WHERE username = ? AND password_hash = ?", (username, hash_pw(password)))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"username": row[0], "elo": row[1], "wins": row[2], "losses": row[3], "draws": row[4]}

def get_user_profile(username):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, elo, wins, losses, draws FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"username": username, "elo": 1000, "wins": 0, "losses": 0, "draws": 0}
    return {"username": row[0], "elo": row[1], "wins": row[2], "losses": row[3], "draws": row[4]}

def get_leaderboard():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username, elo, wins, losses, draws FROM users ORDER BY elo DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

def update_elo_ratings(white_name, black_name, outcome, is_bot_game):
    """outcome: 1.0 = White win, 0.0 = Black win, 0.5 = Draw"""
    conn = get_conn()
    c = conn.cursor()
    w_prof = get_user_profile(white_name) if not white_name.startswith("🤖") else None
    b_prof = get_user_profile(black_name) if not black_name.startswith("🤖") else None

    w_elo = w_prof["elo"] if w_prof else 1000
    b_elo = b_prof["elo"] if b_prof else 1000

    # If bot game, pull bot's static ELO
    for b_data in BOT_PROFILES.values():
        if b_data["name"] == white_name:
            w_elo = b_data["elo"]
        if b_data["name"] == black_name:
            b_elo = b_data["elo"]

    expected_w = 1 / (1 + 10 ** ((b_elo - w_elo) / 400))
    expected_b = 1 - expected_w
    k = 24 if is_bot_game else 32

    if w_prof:
        new_w_elo = max(100, round(w_elo + k * (outcome - expected_w)))
        w_win = 1 if outcome == 1.0 else 0
        w_loss = 1 if outcome == 0.0 else 0
        w_draw = 1 if outcome == 0.5 else 0
        c.execute("""
            UPDATE users SET elo = ?, wins = wins + ?, losses = losses + ?, draws = draws + ?
            WHERE username = ?
        """, (new_w_elo, w_win, w_loss, w_draw, white_name))

    if b_prof:
        new_b_elo = max(100, round(b_elo + k * ((1.0 - outcome) - expected_b)))
        b_win = 1 if outcome == 0.0 else 0
        b_loss = 1 if outcome == 1.0 else 0
        b_draw = 1 if outcome == 0.5 else 0
        c.execute("""
            UPDATE users SET elo = ?, wins = wins + ?, losses = losses + ?, draws = draws + ?
            WHERE username = ?
        """, (new_b_elo, b_win, b_loss, b_draw, black_name))

    conn.commit()
    conn.close()

def generate_room_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_pvp_game(username, base_seconds, increment_seconds):
    prof = get_user_profile(username)
    conn = get_conn()
    c = conn.cursor()
    room_code = generate_room_code()
    c.execute("""
        INSERT INTO games (
            room_code, fen, pgn_moves, last_move_uci, white_player, black_player,
            white_elo, black_elo, is_bot_game, bot_key, status, result_reason, elo_processed,
            time_control, increment, white_time, black_time, last_tick, draw_offer, chat_log
        ) VALUES (?, ?, '', '', ?, NULL, ?, 1000, 0, '', 'waiting', '', 0, ?, ?, ?, ?, 0.0, '', '[]')
    """, (room_code, chess.Board().fen(), username, prof["elo"], base_seconds, increment_seconds, float(base_seconds), float(base_seconds)))
    conn.commit()
    conn.close()
    return room_code

def create_bot_game(username, bot_key, user_side, base_seconds, increment_seconds):
    prof = get_user_profile(username)
    bot_info = BOT_PROFILES[bot_key]
    room_code = "BOT-" + generate_room_code(4)
    board = chess.Board()

    if user_side == "white":
        w_name, b_name = username, bot_info["name"]
        w_elo, b_elo = prof["elo"], bot_info["elo"]
        last_uci = ""
        pgn = ""
    else:
        w_name, b_name = bot_info["name"], username
        w_elo, b_elo = bot_info["elo"], prof["elo"]
        # Bot plays White's opening move immediately
        bot_uci = choose_bot_move(board, bot_key)
        mv = chess.Move.from_uci(bot_uci)
        pgn = board.san(mv)
        board.push(mv)
        last_uci = bot_uci

    now = time.time()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO games (
            room_code, fen, pgn_moves, last_move_uci, white_player, black_player,
            white_elo, black_elo, is_bot_game, bot_key, status, result_reason, elo_processed,
            time_control, increment, white_time, black_time, last_tick, draw_offer, chat_log
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'active', '', 0, ?, ?, ?, ?, ?, '', '[]')
    """, (
        room_code, board.fen(), pgn, last_uci, w_name, b_name, w_elo, b_elo,
        bot_key, base_seconds, increment_seconds, float(base_seconds), float(base_seconds), now
    ))
    conn.commit()
    conn.close()
    return room_code

def join_pvp_game(room_code, username):
    prof = get_user_profile(username)
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT white_player, black_player, is_bot_game FROM games WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, "Room code does not exist."
    white_p, black_p, is_bot = row
    if white_p == username:
        conn.close()
        return "white", None
    if black_p == username:
        conn.close()
        return "black", None
    if black_p is None and not is_bot:
        now = time.time()
        c.execute(
            "UPDATE games SET black_player = ?, black_elo = ?, status = 'active', last_tick = ? WHERE room_code = ?",
            (username, prof["elo"], now, room_code)
        )
        conn.commit()
        conn.close()
        return "black", None
    conn.close()
    return "spectator", None

def get_game(room_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM games WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "room_code", "fen", "pgn_moves", "last_move_uci", "white_player", "black_player",
        "white_elo", "black_elo", "is_bot_game", "bot_key", "status", "result_reason",
        "elo_processed", "time_control", "increment", "white_time", "black_time",
        "last_tick", "draw_offer", "chat_log"
    ]
    return dict(zip(keys, row))

def conclude_match(room_code, reason, outcome):
    game = get_game(room_code)
    if not game or game["elo_processed"] == 1:
        return
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE games SET status = 'finished', result_reason = ?, elo_processed = 1, draw_offer = '' WHERE room_code = ?",
        (reason, room_code)
    )
    conn.commit()
    conn.close()
    update_elo_ratings(game["white_player"], game["black_player"], outcome, bool(game["is_bot_game"]))

def execute_move(room_code, uci_str):
    game = get_game(room_code)
    if not game or game["status"] != "active":
        return

    board = chess.Board(game["fen"])
    try:
        move = chess.Move.from_uci(uci_str)
    except ValueError:
        return
    if move not in board.legal_moves:
        return

    now = time.time()
    w_time = game["white_time"]
    b_time = game["black_time"]
    inc = game["increment"]

    if game["time_control"] > 0 and game["last_tick"] > 0:
        elapsed = now - game["last_tick"]
        if board.turn == chess.WHITE:
            w_time = max(0.0, w_time - elapsed)
            if w_time == 0:
                conclude_match(room_code, "Black wins on time!", 0.0)
                return
            w_time += inc
        else:
            b_time = max(0.0, b_time - elapsed)
            if b_time == 0:
                conclude_match(room_code, "White wins on time!", 1.0)
                return
            b_time += inc

    san = board.san(move)
    board.push(move)
    new_pgn = (game["pgn_moves"] + " " + san).strip()
    last_uci = uci_str

    # Check if human move ended the game
    if board.is_game_over():
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            "UPDATE games SET fen = ?, pgn_moves = ?, last_move_uci = ?, white_time = ?, black_time = ? WHERE room_code = ?",
            (board.fen(), new_pgn, last_uci, w_time, b_time, room_code)
        )
        conn.commit()
        conn.close()
        if board.is_checkmate():
            winner = "White" if board.turn == chess.BLACK else "Black"
            outcome = 1.0 if winner == "White" else 0.0
            conclude_match(room_code, f"Checkmate! {winner} wins.", outcome)
        else:
            conclude_match(room_code, "Match drawn.", 0.5)
        return

    # If playing vs Bot, trigger bot's immediate response
    if game["is_bot_game"] == 1:
        bot_uci = choose_bot_move(board, game["bot_key"])
        if bot_uci:
            bot_move = chess.Move.from_uci(bot_uci)
            bot_san = board.san(bot_move)
            board.push(bot_move)
            new_pgn = (new_pgn + " " + bot_san).strip()
            last_uci = bot_uci
            if game["time_control"] > 0:
                if board.turn == chess.WHITE:
                    b_time += inc
                else:
                    w_time += inc

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE games
        SET fen = ?, pgn_moves = ?, last_move_uci = ?, white_time = ?, black_time = ?,
            last_tick = ?, draw_offer = ''
        WHERE room_code = ?
    """, (board.fen(), new_pgn, last_uci, w_time, b_time, time.time(), room_code))
    conn.commit()
    conn.close()

    # Check if bot's move ended the game
    if board.is_game_over():
        if board.is_checkmate():
            winner = "White" if board.turn == chess.BLACK else "Black"
            outcome = 1.0 if winner == "White" else 0.0
            conclude_match(room_code, f"Checkmate! {winner} wins.", outcome)
        else:
            conclude_match(room_code, "Match drawn.", 0.5)

def set_draw_offer(room_code, offer_from):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE games SET draw_offer = ? WHERE room_code = ?", (offer_from, room_code))
    conn.commit()
    conn.close()

def send_chat(room_code, sender, text):
    game = get_game(room_code)
    if not game:
        return
    logs = json.loads(game["chat_log"])
    logs.append({"sender": sender, "text": text})
    logs = logs[-30:]
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE games SET chat_log = ? WHERE room_code = ?", (json.dumps(logs), room_code))
    conn.commit()
    conn.close()

def reset_match(room_code):
    game = get_game(room_code)
    if not game:
        return
    base = float(game["time_control"])
    board = chess.Board()
    last_uci = ""
    pgn = ""

    if game["is_bot_game"] == 1 and game["white_player"].startswith("🤖"):
        bot_uci = choose_bot_move(board, game["bot_key"])
        mv = chess.Move.from_uci(bot_uci)
        pgn = board.san(mv)
        board.push(mv)
        last_uci = bot_uci

    status = "active" if (game["black_player"] or game["is_bot_game"] == 1) else "waiting"
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE games
        SET fen = ?, pgn_moves = ?, last_move_uci = ?, status = ?, result_reason = '',
            elo_processed = 0, white_time = ?, black_time = ?, last_tick = ?, draw_offer = ''
        WHERE room_code = ?
    """, (board.fen(), pgn, last_uci, status, base, base, time.time(), room_code))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 4. Material & Clock Helpers
# ==========================================
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
UNICODE_PIECES = {'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛'}

def get_material_info(board):
    start_counts = {'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1, 'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1}
    for ch in board.fen().split()[0]:
        if ch in start_counts:
            start_counts[ch] -= 1
    cap_by_w = "".join(UNICODE_PIECES[p] * max(0, start_counts[p]) for p in ['q', 'r', 'b', 'n', 'p'])
    cap_by_b = "".join(UNICODE_PIECES[p] * max(0, start_counts[p]) for p in ['Q', 'R', 'B', 'N', 'P'])
    w_mat = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in PIECE_VALUES.items())
    b_mat = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in PIECE_VALUES.items())
    return cap_by_w, cap_by_b, w_mat - b_mat

def format_clock(seconds):
    if seconds <= 0:
        return "00:00"
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

# ==========================================
# 5. Interactive Click-to-Move Board Component
# ==========================================
THEMES = {
    "Obsidian Gold": ("#e2e8f0", "#475569"),
    "Emerald Tournament": ("#eeeed2", "#769656"),
    "Royal Walnut": ("#f0d9b5", "#b58863"),
}

def interactive_chessboard(board, flipped, can_move, last_move_uci, theme_colors, move_count):
    light_sq, dark_sq = theme_colors
    legal_moves = [m.uci() for m in board.legal_moves] if can_move else []
    in_check_sq = chess.square_name(board.king(board.turn)) if board.is_check() else ""

    sound_event = "none"
    if move_count > 0:
        if board.is_game_over():
            sound_event = "gameover"
        elif board.is_check():
            sound_event = "check"
        else:
            sound_event = "move"

    board_map = {}
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            board_map[chess.square_name(sq)] = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0; background: transparent;
            display: flex; justify-content: center; align-items: center;
            font-family: 'Inter', sans-serif; user-select: none;
        }}
        #board-wrapper {{
            position: relative; width: 480px; height: 480px;
            border: 3px solid #2d3446; border-radius: 10px; overflow: hidden;
            box-shadow: 0 16px 40px rgba(0,0,0,0.65);
            display: grid; grid-template-columns: repeat(8, 1fr); grid-template-rows: repeat(8, 1fr);
        }}
        .square {{
            width: 60px; height: 60px; position: relative;
            display: flex; justify-content: center; align-items: center; cursor: pointer;
        }}
        .light {{ background-color: {light_sq}; }}
        .dark {{ background-color: {dark_sq}; }}
        .selected {{ background-color: rgba(212, 175, 55, 0.7) !important; }}
        .last-move {{ background-color: rgba(212, 175, 55, 0.42) !important; }}
        .in-check {{ background: radial-gradient(circle, rgba(239,68,68,0.9) 0%, rgba(239,68,68,0.3) 70%, transparent 100%) !important; }}
        .piece-img {{ width: 52px; height: 52px; z-index: 2; transition: transform 0.08s ease; pointer-events: none; }}
        .square:hover .piece-img {{ transform: scale(1.07); }}
        .hint-dot {{ width: 16px; height: 16px; background: rgba(15, 23, 42, 0.28); border-radius: 50%; z-index: 3; pointer-events: none; }}
        .hint-capture {{ width: 52px; height: 52px; border: 5px solid rgba(15, 23, 42, 0.3); border-radius: 50%; position: absolute; z-index: 3; pointer-events: none; box-sizing: border-box; }}
        .coord-rank {{ position: absolute; top: 2px; left: 4px; font-size: 10px; font-weight: 800; opacity: 0.75; }}
        .coord-file {{ position: absolute; bottom: 2px; right: 4px; font-size: 10px; font-weight: 800; opacity: 0.75; }}
        #promo-overlay {{
            display: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(11, 13, 17, 0.85); z-index: 10; justify-content: center; align-items: center; gap: 14px;
        }}
        .promo-btn {{ background: #1e293b; border-radius: 10px; padding: 10px; cursor: pointer; border: 2px solid #d4af37; }}
        .promo-btn:hover {{ transform: scale(1.1); }}
    </style>
    </head>
    <body>
        <div id="board-wrapper"><div id="promo-overlay"></div></div>
        <script>
            function sendMsg(type, data) {{
                window.parent.postMessage(Object.assign({{ isStreamlitMessage: true, type: type }}, data), "*");
            }}
            function initStreamlit() {{
                sendMsg("streamlit:componentReady", {{ apiVersion: 1 }});
                sendMsg("streamlit:setFrameHeight", {{ height: 495 }});
            }}
            function submitMove(uci) {{
                sendMsg("streamlit:setComponentValue", {{ value: uci }});
            }}

            const soundEvent = "{sound_event}";
            const moveCount = {move_count};
            function playSound(type) {{
                if (type === "none") return;
                if (sessionStorage.getItem("aurelia_snd") == String(moveCount)) return;
                sessionStorage.setItem("aurelia_snd", String(moveCount));
                try {{
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain); gain.connect(ctx.destination);
                    if (type === "move") {{
                        osc.type = "triangle";
                        osc.frequency.setValueAtTime(175, ctx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(65, ctx.currentTime + 0.08);
                        gain.gain.setValueAtTime(0.3, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);
                        osc.start(); osc.stop(ctx.currentTime + 0.08);
                    }} else if (type === "check") {{
                        osc.type = "sawtooth";
                        osc.frequency.setValueAtTime(460, ctx.currentTime);
                        osc.frequency.setValueAtTime(610, ctx.currentTime + 0.09);
                        gain.gain.setValueAtTime(0.25, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.22);
                        osc.start(); osc.stop(ctx.currentTime + 0.22);
                    }} else if (type === "gameover") {{
                        osc.type = "sine";
                        osc.frequency.setValueAtTime(523.25, ctx.currentTime);
                        osc.frequency.setValueAtTime(392.00, ctx.currentTime + 0.15);
                        osc.frequency.setValueAtTime(261.63, ctx.currentTime + 0.3);
                        gain.gain.setValueAtTime(0.3, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
                        osc.start(); osc.stop(ctx.currentTime + 0.5);
                    }}
                }} catch(e) {{}}
            }}

            const PIECE_URLS = {{
                wP: "https://upload.wikimedia.org/wikipedia/commons/4/45/Chess_plt45.svg",
                wN: "https://upload.wikimedia.org/wikipedia/commons/7/70/Chess_nlt45.svg",
                wB: "https://upload.wikimedia.org/wikipedia/commons/b/b1/Chess_blt45.svg",
                wR: "https://upload.wikimedia.org/wikipedia/commons/7/72/Chess_rlt45.svg",
                wQ: "https://upload.wikimedia.org/wikipedia/commons/1/15/Chess_qlt45.svg",
                wK: "https://upload.wikimedia.org/wikipedia/commons/4/42/Chess_klt45.svg",
                bP: "https://upload.wikimedia.org/wikipedia/commons/c/c7/Chess_pdt45.svg",
                bN: "https://upload.wikimedia.org/wikipedia/commons/e/ef/Chess_ndt45.svg",
                bB: "https://upload.wikimedia.org/wikipedia/commons/9/98/Chess_bdt45.svg",
                bR: "https://upload.wikimedia.org/wikipedia/commons/f/ff/Chess_rdt45.svg",
                bQ: "https://upload.wikimedia.org/wikipedia/commons/4/47/Chess_qdt45.svg",
                bK: "https://upload.wikimedia.org/wikipedia/commons/f/f0/Chess_kdt45.svg"
            }};

            const boardMap = {json.dumps(board_map)};
            const legalMoves = {json.dumps(legal_moves)};
            const flipped = {json.dumps(flipped)};
            const canMove = {json.dumps(can_move)};
            const lastMove = "{last_move_uci}";
            const checkSq = "{in_check_sq}";
            const turnColor = "{ 'w' if board.turn == chess.WHITE else 'b' }";
            let selectedSq = null;

            function render() {{
                const wrapper = document.getElementById("board-wrapper");
                const promoOverlay = document.getElementById("promo-overlay");
                wrapper.innerHTML = "";
                wrapper.appendChild(promoOverlay);

                const files = flipped ? ['h','g','f','e','d','c','b','a'] : ['a','b','c','d','e','f','g','h'];
                const ranks = flipped ? ['1','2','3','4','5','6','7','8'] : ['8','7','6','5','4','3','2','1'];
                const validTargets = selectedSq ? legalMoves.filter(m => m.startsWith(selectedSq)).map(m => m.slice(2, 4)) : [];

                for (let r = 0; r < 8; r++) {{
                    for (let c = 0; c < 8; c++) {{
                        const sqName = files[c] + ranks[r];
                        const isLight = ((files[c].charCodeAt(0) - 97) + (parseInt(ranks[r]) - 1)) % 2 !== 0;
                        const sqDiv = document.createElement("div");
                        sqDiv.className = "square " + (isLight ? "light" : "dark");

                        if (lastMove && (lastMove.slice(0,2) === sqName || lastMove.slice(2,4) === sqName)) sqDiv.classList.add("last-move");
                        if (sqName === checkSq) sqDiv.classList.add("in-check");
                        if (sqName === selectedSq) sqDiv.classList.add("selected");

                        if (c === 0) {{
                            const rSpan = document.createElement("span");
                            rSpan.className = "coord-rank"; rSpan.style.color = isLight ? "{dark_sq}" : "{light_sq}";
                            rSpan.innerText = ranks[r]; sqDiv.appendChild(rSpan);
                        }}
                        if (r === 7) {{
                            const fSpan = document.createElement("span");
                            fSpan.className = "coord-file"; fSpan.style.color = isLight ? "{dark_sq}" : "{light_sq}";
                            fSpan.innerText = files[c]; sqDiv.appendChild(fSpan);
                        }}
                        if (boardMap[sqName]) {{
                            const img = document.createElement("img");
                            img.src = PIECE_URLS[boardMap[sqName]]; img.className = "piece-img";
                            sqDiv.appendChild(img);
                        }}
                        if (validTargets.includes(sqName)) {{
                            const hint = document.createElement("div");
                            hint.className = boardMap[sqName] ? "hint-capture" : "hint-dot";
                            sqDiv.appendChild(hint);
                        }}
                        sqDiv.onclick = () => handleSquareClick(sqName);
                        wrapper.appendChild(sqDiv);
                    }}
                }}
            }}

            function handleSquareClick(sq) {{
                if (!canMove) return;
                if (selectedSq) {{
                    const matches = legalMoves.filter(m => m.startsWith(selectedSq + sq));
                    if (matches.length > 0) {{
                        if (matches[0].length === 5) showPromotionPicker(selectedSq, sq);
                        else submitMove(matches[0]);
                        selectedSq = null; render(); return;
                    }}
                }}
                selectedSq = (boardMap[sq] && boardMap[sq].startsWith(turnColor) && selectedSq !== sq) ? sq : null;
                render();
            }}

            function showPromotionPicker(fromSq, toSq) {{
                const overlay = document.getElementById("promo-overlay");
                overlay.innerHTML = ""; overlay.style.display = "flex";
                ['q', 'r', 'b', 'n'].forEach(p => {{
                    const btn = document.createElement("div"); btn.className = "promo-btn";
                    const img = document.createElement("img"); img.src = PIECE_URLS[turnColor + p.toUpperCase()];
                    img.style.width = "48px"; img.style.height = "48px"; btn.appendChild(img);
                    btn.onclick = (e) => {{ e.stopPropagation(); overlay.style.display = "none"; submitMove(fromSq + toSq + p); }};
                    overlay.appendChild(btn);
                }});
            }}

            initStreamlit(); render(); playSound(soundEvent);
        </script>
    </body>
    </html>
    """
    return components.html(html_code, height=495)

# ==========================================
# 6. Session State
# ==========================================
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "room_code" not in st.session_state:
    st.session_state.room_code = None
if "role" not in st.session_state:
    st.session_state.role = None
if "last_processed_uci" not in st.session_state:
    st.session_state.last_processed_uci = ""
if "board_theme" not in st.session_state:
    st.session_state.board_theme = "Obsidian Gold"

# ==========================================
# 7. Gate 1: Authentication (Login / Register)
# ==========================================
if not st.session_state.auth_user:
    col_spacer1, col_auth, col_spacer2 = st.columns([1, 1.3, 1])
    with col_auth:
        st.markdown('<div class="brand-title">♛ AURELIA CHESS</div>', unsafe_allow_html=True)
        st.markdown('<div class="brand-sub">Ranked Online Multiplayer & AI Grandmaster Arena</div>', unsafe_allow_html=True)

        with st.container(border=True):
            tab_in, tab_up = st.tabs(["🔐 Sign In", "✨ Create Account"])

            with tab_in:
                u_in = st.text_input("Username", key="login_u", placeholder="Enter your username")
                p_in = st.text_input("Password", type="password", key="login_p", placeholder="••••••••")
                if st.button("Enter Arena", type="primary", use_container_width=True):
                    if u_in and p_in:
                        user_obj = authenticate_account(u_in.strip(), p_in)
                        if user_obj:
                            st.session_state.auth_user = user_obj["username"]
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    else:
                        st.warning("Please enter your credentials.")

            with tab_up:
                u_reg = st.text_input("Choose Username", key="reg_u", placeholder="e.g. YoussefGM")
                p_reg = st.text_input("Password", type="password", key="reg_p", placeholder="Min 4 characters")
                p_conf = st.text_input("Confirm Password", type="password", key="reg_c", placeholder="Repeat password")
                if st.button("Create Ranked Account", type="primary", use_container_width=True):
                    if not u_reg.strip() or len(p_reg) < 4:
                        st.warning("Username required and password must be at least 4 characters.")
                    elif p_reg != p_conf:
                        st.error("Passwords do not match.")
                    else:
                        if register_account(u_reg.strip(), p_reg):
                            st.session_state.auth_user = u_reg.strip()
                            st.rerun()
                        else:
                            st.error("That username is already taken.")

# ==========================================
# 8. Gate 2: Main Studio Lobby (PvP + Bots + Leaderboard)
# ==========================================
elif not st.session_state.room_code:
    profile = get_user_profile(st.session_state.auth_user)

    # Top Navigation Header
    h_left, h_right = st.columns([3, 1])
    with h_left:
        st.markdown('<div class="brand-title">♛ AURELIA CHESS</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brand-sub">Welcome back, <strong>{profile["username"]}</strong> — Ready for your next match.</div>', unsafe_allow_html=True)
    with h_right:
        st.write("")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.auth_user = None
            st.session_state.room_code = None
            st.rerun()

    # Player Profile Stat Banner
    st.markdown(f"""
        <div class="glass-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:1.15rem; font-weight:700;">👤 {profile['username']}</span>
                    <span class="elo-tag" style="margin-left:10px;">RATING: {profile['elo']} ELO</span>
                </div>
                <span style="color:#64748b; font-size:0.85rem;">Season 1 • Ranked Active</span>
            </div>
            <div class="stat-grid">
                <div class="stat-box"><div class="stat-val">{profile['elo']}</div><div class="stat-lbl">Current ELO</div></div>
                <div class="stat-box"><div class="stat-val" style="color:#34d399;">{profile['wins']}</div><div class="stat-lbl">Wins</div></div>
                <div class="stat-box"><div class="stat-val" style="color:#f87171;">{profile['losses']}</div><div class="stat-lbl">Losses</div></div>
                <div class="stat-box"><div class="stat-val" style="color:#94a3b8;">{profile['draws']}</div><div class="stat-lbl">Draws</div></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_modes, col_board_rank = st.columns([1.6, 1], gap="large")

    with col_modes:
        tab_bots, tab_pvp = st.tabs(["🤖 Play vs AI Bots", "⚔️ Online PvP Arena"])

        # --- TAB 1: BOTS ---
        with tab_bots:
            st.markdown("#### Select Opponent & Match Settings")
            c_bot1, c_bot2 = st.columns(2)
            with c_bot1:
                selected_bot = st.selectbox("Choose AI Bot", list(BOT_PROFILES.keys()))
                bot_meta = BOT_PROFILES[selected_bot]
                st.markdown(f"""
                    <div class="glass-card" style="padding:12px 15px;">
                        <span class="bot-badge">{bot_meta['elo']} ELO</span>
                        <p style="margin-top:8px; margin-bottom:0; font-size:0.88rem; color:#cbd5e1;">{bot_meta['desc']}</p>
                    </div>
                """, unsafe_allow_html=True)

            with c_bot2:
                side_choice = st.radio("Play As", ["White (First Move)", "Black", "Random"], horizontal=True)
                bot_tc = st.selectbox(
                    "Time Control",
                    options=[("Unlimited (Practice)", 0, 0), ("Rapid 10+0", 600, 0), ("Blitz 3+2", 180, 2), ("Bullet 1+0", 60, 0)],
                    format_func=lambda x: x[0],
                    key="bot_tc"
                )

            if st.button("⚡ Start Bot Match", type="primary", use_container_width=True):
                chosen_side = "white" if "White" in side_choice else ("black" if "Black" in side_choice else random.choice(["white", "black"]))
                code = create_bot_game(profile["username"], selected_bot, chosen_side, bot_tc[1], bot_tc[2])
                st.session_state.room_code = code
                st.session_state.role = chosen_side
                st.session_state.last_processed_uci = ""
                st.rerun()

        # --- TAB 2: MULTIPLAYER PVP ---
        with tab_pvp:
            pvp_c1, pvp_c2 = st.columns(2, gap="medium")
            with pvp_c1:
                with st.container(border=True):
                    st.markdown("##### Host Ranked Room")
                    pvp_tc = st.selectbox(
                        "Time Control",
                        options=[("Rapid 10+0", 600, 0), ("Blitz 3+2", 180, 2), ("Bullet 1+0", 60, 0), ("Unlimited", 0, 0)],
                        format_func=lambda x: x[0],
                        key="pvp_tc"
                    )
                    if st.button("➕ Create Room", type="primary", use_container_width=True):
                        code = create_pvp_game(profile["username"], pvp_tc[1], pvp_tc[2])
                        st.session_state.room_code = code
                        st.session_state.role = "white"
                        st.session_state.last_processed_uci = ""
                        st.rerun()

            with pvp_c2:
                with st.container(border=True):
                    st.markdown("##### Join Friend's Room")
                    join_code = st.text_input("Enter Room Code", placeholder="e.g. X9K2M").upper().strip()
                    st.write("")
                    if st.button("⚔️ Join Match", use_container_width=True):
                        if not join_code:
                            st.warning("Enter a room code first.")
                        else:
                            role, err = join_pvp_game(join_code, profile["username"])
                            if err:
                                st.error(err)
                            else:
                                st.session_state.room_code = join_code
                                st.session_state.role = role
                                st.session_state.last_processed_uci = ""
                                st.rerun()

    with col_board_rank:
        st.markdown("#### 🏆 Global ELO Leaderboard")
        leaders = get_leaderboard()
        with st.container(border=True):
            if leaders:
                md_table = "| Rank | Player | ELO | W / L / D |\n|---|---|---|---|\n"
                for idx, (u_name, u_elo, w, l, d) in enumerate(leaders, start=1):
                    medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"#{idx}"))
                    md_table += f"| {medal} | **{u_name}** | `{u_elo}` | {w}/{l}/{d} |\n"
                st.markdown(md_table)

# ==========================================
# 9. Gate 3: Live Match Arena
# ==========================================
else:
    with st.sidebar:
        st.markdown('<div class="brand-title" style="font-size:1.5rem;">♛ AURELIA</div>', unsafe_allow_html=True)
        st.caption("Room Invite Code")
        st.code(st.session_state.room_code, language=None)
        st.write(f"**Account:** {st.session_state.auth_user}")
        st.write(f"**Playing As:** {st.session_state.role.capitalize()}")

        st.divider()
        st.session_state.board_theme = st.selectbox("Board Palette", list(THEMES.keys()))

        st.divider()
        if st.session_state.role in ["white", "black"]:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🏳️ Resign", use_container_width=True):
                    winner = "Black" if st.session_state.role == "white" else "White"
                    outcome = 0.0 if st.session_state.role == "white" else 1.0
                    conclude_match(st.session_state.room_code, f"{st.session_state.role.capitalize()} resigned. {winner} wins!", outcome)
                    st.rerun()
            with c2:
                if st.button("🤝 Draw", use_container_width=True):
                    game_chk = get_game(st.session_state.room_code)
                    if game_chk and game_chk["is_bot_game"] == 1:
                        st.toast("Bots do not accept draw offers!")
                    else:
                        set_draw_offer(st.session_state.room_code, st.session_state.role)
                        st.rerun()

        if st.button("🔄 Rematch", use_container_width=True):
            st.session_state.last_processed_uci = ""
            reset_match(st.session_state.room_code)
            st.rerun()

        if st.button("⬅️ Exit to Lobby", use_container_width=True):
            st.session_state.room_code = None
            st.session_state.role = None
            st.rerun()

    @st.fragment(run_every=1)
    def render_arena():
        game = get_game(st.session_state.room_code)
        if not game:
            st.error("Match session ended.")
            return

        board = chess.Board(game["fen"])
        now = time.time()

        w_time = game["white_time"]
        b_time = game["black_time"]
        has_clock = game["time_control"] > 0

        if has_clock and game["status"] == "active" and game["last_tick"] > 0:
            elapsed = now - game["last_tick"]
            if board.turn == chess.WHITE:
                w_time = max(0.0, w_time - elapsed)
                if w_time == 0:
                    conclude_match(st.session_state.room_code, "Black wins on time!", 0.0)
                    st.rerun()
            else:
                b_time = max(0.0, b_time - elapsed)
                if b_time == 0:
                    conclude_match(st.session_state.room_code, "White wins on time!", 1.0)
                    st.rerun()

        # Draw offer alert
        if game["draw_offer"] and game["status"] == "active":
            opp_role = "black" if game["draw_offer"] == "white" else "white"
            if st.session_state.role == opp_role:
                st.warning(f"🤝 {game['draw_offer'].capitalize()} has offered a draw.")
                b_acc, b_dec = st.columns(2)
                if b_acc.button("✅ Accept Draw", use_container_width=True):
                    conclude_match(st.session_state.room_code, "Draw by mutual agreement.", 0.5)
                    st.rerun()
                if b_dec.button("❌ Decline", use_container_width=True):
                    set_draw_offer(st.session_state.room_code, "")
                    st.rerun()

        if game["status"] == "waiting":
            st.info(f"⏳ Waiting for opponent to join Room **{st.session_state.room_code}**...")
        elif game["status"] == "finished":
            st.success(f"🏆 **{game['result_reason']}** (ELO Ratings Updated)")

        cap_by_w, cap_by_b, mat_diff = get_material_info(board)
        flipped = (st.session_state.role == "black")

        top_name = game["white_player"] if flipped else (game["black_player"] or "Waiting...")
        bot_name = (game["black_player"] or "Waiting...") if flipped else game["white_player"]
        top_elo = game["white_elo"] if flipped else game["black_elo"]
        bot_elo = game["black_elo"] if flipped else game["white_elo"]
        top_time = w_time if flipped else b_time
        bot_time = b_time if flipped else w_time
        top_cap = cap_by_w if flipped else cap_by_b
        bot_cap = cap_by_b if flipped else cap_by_w
        top_adv = f"+{mat_diff}" if (flipped and mat_diff > 0) else (f"+{-mat_diff}" if (not flipped and mat_diff < 0) else "")
        bot_adv = f"+{-mat_diff}" if (flipped and mat_diff < 0) else (f"+{mat_diff}" if (not flipped and mat_diff > 0) else "")
        top_active = (board.turn == chess.WHITE) if flipped else (board.turn == chess.BLACK)
        bot_active = not top_active

        col_board, col_panel = st.columns([1.35, 1], gap="large")

        with col_board:
            # Top Opponent Bar
            t_cls = "running" if (top_active and game["status"] == "active") else ""
            if has_clock and top_time < 20:
                t_cls = "danger"
            t_clock = f'<div class="clock-pill {t_cls}">{format_clock(top_time)}</div>' if has_clock else ""
            t_plus = f'<span class="mat-plus">{top_adv}</span>' if top_adv else ""
            st.markdown(f"""
                <div class="arena-bar {'active' if top_active else ''}">
                    <div>
                        <div class="player-meta">
                            <strong>{'⚪' if flipped else '⚫'} {top_name}</strong>
                            <span class="elo-tag">{top_elo}</span>
                            {t_plus}
                        </div>
                        <div class="cap-strip">{top_cap}</div>
                    </div>
                    {t_clock}
                </div>
            """, unsafe_allow_html=True)

            # Interactive Chessboard
            is_my_turn = (
                game["status"] == "active"
                and (
                    (board.turn == chess.WHITE and st.session_state.role == "white")
                    or (board.turn == chess.BLACK and st.session_state.role == "black")
                )
            )
            clicked_uci = interactive_chessboard(
                board=board,
                flipped=flipped,
                can_move=is_my_turn,
                last_move_uci=game["last_move_uci"],
                theme_colors=THEMES[st.session_state.board_theme],
                move_count=len(game["pgn_moves"].split())
            )

            if clicked_uci and isinstance(clicked_uci, str) and clicked_uci != st.session_state.last_processed_uci:
                st.session_state.last_processed_uci = clicked_uci
                execute_move(st.session_state.room_code, clicked_uci)
                st.rerun()

            # Bottom Player Bar
            b_cls = "running" if (bot_active and game["status"] == "active") else ""
            if has_clock and bot_time < 20:
                b_cls = "danger"
            b_clock = f'<div class="clock-pill {b_cls}">{format_clock(bot_time)}</div>' if has_clock else ""
            b_plus = f'<span class="mat-plus">{bot_adv}</span>' if bot_adv else ""
            st.markdown(f"""
                <div class="arena-bar {'active' if bot_active else ''}">
                    <div>
                        <div class="player-meta">
                            <strong>{'⚫' if flipped else '⚪'} {bot_name}</strong>
                            <span class="elo-tag">{bot_elo}</span>
                            {b_plus}
                        </div>
                        <div class="cap-strip">{bot_cap}</div>
                    </div>
                    {b_clock}
                </div>
            """, unsafe_allow_html=True)

        with col_panel:
            st.markdown('<div class="glass-card" style="padding:12px 16px;">', unsafe_allow_html=True)
            t_moves, t_chat = st.tabs(["📜 Algebraic Move Sheet", "💬 Arena Chat"])

            with t_moves:
                moves = game["pgn_moves"].split()
                if moves:
                    md = "| Move | White | Black |\n|---|---|---|\n"
                    for i in range(0, len(moves), 2):
                        md += f"| {(i // 2) + 1}. | **{moves[i]}** | **{moves[i+1] if i+1 < len(moves) else ''}** |\n"
                    st.markdown(md)
                    st.download_button("⬇️ Export Match PGN", data=game["pgn_moves"], file_name=f"aurelia_{st.session_state.room_code}.pgn", use_container_width=True)
                else:
                    st.caption("Click any piece on the board to initiate the match.")

            with t_chat:
                logs = json.loads(game["chat_log"])
                c_box = st.container(height=280)
                with c_box:
                    if not logs:
                        st.caption("No messages in arena chat yet.")
                    for item in logs:
                        st.markdown(f"**{item['sender']}:** {item['text']}")
                with st.form("arena_chat_form", clear_on_submit=True):
                    in_c, btn_c = st.columns([4, 1])
                    txt = in_c.text_input("Chat", label_visibility="collapsed", placeholder="Send message...")
                    if btn_c.form_submit_button("Send") and txt.strip():
                        send_chat(st.session_state.room_code, st.session_state.auth_user, txt.strip())
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    render_arena()