import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import chess
import random
import string
import time
import json

st.set_page_config(page_title="Grandmaster Live Chess", page_icon="♚", layout="wide")

# ==========================================
# 1. Custom Dark UI Styling
# ==========================================
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .player-card {
        background: #1e2128;
        border: 1px solid #2e333d;
        border-radius: 10px;
        padding: 10px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .player-card.active-turn {
        border-color: #81b64c;
        box-shadow: 0 0 12px rgba(129, 182, 76, 0.25);
    }
    .clock-box {
        font-family: 'Courier New', monospace;
        font-size: 1.5rem;
        font-weight: bold;
        padding: 4px 12px;
        border-radius: 6px;
        background: #121418;
        color: #888;
    }
    .clock-box.running {
        background: #ffffff;
        color: #111111;
    }
    .clock-box.low-time {
        background: #d9383a;
        color: #ffffff;
    }
    .captured-row {
        font-size: 1.15rem;
        min-height: 24px;
        color: #ccc;
    }
    .adv-badge {
        background: #2f3542;
        color: #81b64c;
        font-size: 0.8rem;
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Database Layer (SQLite with Clocks, Chat & Draws)
# ==========================================
DB_FILE = "pro_chess.db"

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS games (
            room_code TEXT PRIMARY KEY,
            fen TEXT NOT NULL,
            pgn_moves TEXT DEFAULT '',
            last_move_uci TEXT DEFAULT '',
            white_player TEXT,
            black_player TEXT,
            status TEXT DEFAULT 'waiting',
            result_reason TEXT DEFAULT '',
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

def generate_room_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_game(player_name, base_seconds, increment_seconds):
    conn = get_conn()
    c = conn.cursor()
    room_code = generate_room_code()
    initial_fen = chess.Board().fen()
    c.execute("""
        INSERT INTO games (
            room_code, fen, pgn_moves, last_move_uci, white_player, black_player,
            status, result_reason, time_control, increment, white_time, black_time, last_tick, draw_offer, chat_log
        ) VALUES (?, ?, '', '', ?, NULL, 'waiting', '', ?, ?, ?, ?, 0.0, '', '[]')
    """, (room_code, initial_fen, player_name, base_seconds, increment_seconds, float(base_seconds), float(base_seconds)))
    conn.commit()
    conn.close()
    return room_code

def join_game(room_code, player_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT white_player, black_player, status FROM games WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None, "Room not found."
    white_p, black_p, status = row
    if white_p == player_name:
        conn.close()
        return "white", None
    if black_p == player_name:
        conn.close()
        return "black", None
    if black_p is None:
        now = time.time()
        c.execute("UPDATE games SET black_player = ?, status = 'active', last_tick = ? WHERE room_code = ?", (player_name, now, room_code))
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
        "status", "result_reason", "time_control", "increment", "white_time", "black_time",
        "last_tick", "draw_offer", "chat_log"
    ]
    return dict(zip(keys, row))

def apply_move_db(room_code, uci_str):
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

    # Deduct elapsed time for moving side & add increment
    if game["time_control"] > 0 and game["last_tick"] > 0:
        elapsed = now - game["last_tick"]
        if board.turn == chess.WHITE:
            w_time = max(0.0, w_time - elapsed)
            if w_time == 0:
                finish_game(room_code, "Black wins on time!")
                return
            w_time += inc
        else:
            b_time = max(0.0, b_time - elapsed)
            if b_time == 0:
                finish_game(room_code, "White wins on time!")
                return
            b_time += inc

    san = board.san(move)
    board.push(move)
    new_pgn = (game["pgn_moves"] + " " + san).strip()

    new_status = "active"
    reason = ""
    if board.is_checkmate():
        new_status = "finished"
        winner = "White" if board.turn == chess.BLACK else "Black"
        reason = f"Checkmate! {winner} wins."
    elif board.is_stalemate():
        new_status = "finished"
        reason = "Draw by stalemate."
    elif board.is_insufficient_material():
        new_status = "finished"
        reason = "Draw by insufficient material."
    elif board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
        new_status = "finished"
        reason = "Draw by repetition / 50-move rule."

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE games
        SET fen = ?, pgn_moves = ?, last_move_uci = ?, white_time = ?, black_time = ?,
            last_tick = ?, status = ?, result_reason = ?, draw_offer = ''
        WHERE room_code = ?
    """, (board.fen(), new_pgn, uci_str, w_time, b_time, now, new_status, reason, room_code))
    conn.commit()
    conn.close()

def finish_game(room_code, reason):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE games SET status = 'finished', result_reason = ?, draw_offer = '' WHERE room_code = ?", (reason, room_code))
    conn.commit()
    conn.close()

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
    logs = logs[-30:]  # keep last 30 messages
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE games SET chat_log = ? WHERE room_code = ?", (json.dumps(logs), room_code))
    conn.commit()
    conn.close()

def reset_game(room_code):
    game = get_game(room_code)
    if not game:
        return
    base = float(game["time_control"])
    now = time.time() if game["black_player"] else 0.0
    status = "active" if game["black_player"] else "waiting"
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE games
        SET fen = ?, pgn_moves = '', last_move_uci = '', status = ?, result_reason = '',
            white_time = ?, black_time = ?, last_tick = ?, draw_offer = ''
        WHERE room_code = ?
    """, (chess.Board().fen(), status, base, base, now, room_code))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. Helpers: Material, Captured Pieces & Clock Formatting
# ==========================================
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
UNICODE_PIECES = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛'
}

def get_material_info(board):
    start_counts = {'P': 8, 'N': 2, 'B': 2, 'R': 2, 'Q': 1, 'p': 8, 'n': 2, 'b': 2, 'r': 2, 'q': 1}
    current_fen_board = board.fen().split()[0]
    for ch in current_fen_board:
        if ch in start_counts:
            start_counts[ch] -= 1

    # Pieces captured BY White (black pieces missing)
    captured_by_white = "".join(UNICODE_PIECES[p] * max(0, start_counts[p]) for p in ['q', 'r', 'b', 'n', 'p'])
    # Pieces captured BY Black (white pieces missing)
    captured_by_black = "".join(UNICODE_PIECES[p] * max(0, start_counts[p]) for p in ['Q', 'R', 'B', 'N', 'P'])

    w_mat = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in PIECE_VALUES.items())
    b_mat = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in PIECE_VALUES.items())
    diff = w_mat - b_mat
    return captured_by_white, captured_by_black, diff

def format_clock(seconds):
    if seconds <= 0:
        return "00:00"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

# ==========================================
# 4. Interactive HTML/JS Click-to-Move Board Component
# ==========================================
THEMES = {
    "Tournament Green": ("#eeeed2", "#769656"),
    "Championship Blue": ("#dee3e6", "#8ca2ad"),
    "Classic Walnut": ("#f0d9b5", "#b58863"),
}

def interactive_chessboard(board, flipped, can_move, last_move_uci, theme_colors, move_count):
    light_sq, dark_sq = theme_colors
    legal_moves = [m.uci() for m in board.legal_moves] if can_move else []
    in_check_sq = chess.square_name(board.king(board.turn)) if board.is_check() else ""
    
    # Sound trigger type
    sound_event = "none"
    if move_count > 0:
        if board.is_checkmate() or board.is_game_over():
            sound_event = "gameover"
        elif board.is_check():
            sound_event = "check"
        else:
            sound_event = "move"

    # Build board map { "e2": "wP", ... }
    board_map = {}
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            color_prefix = "w" if piece.color == chess.WHITE else "b"
            board_map[chess.square_name(sq)] = color_prefix + piece.symbol().upper()

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            background: transparent;
            display: flex;
            flex-direction: column;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            user-select: none;
        }}
        #board-wrapper {{
            position: relative;
            width: 480px;
            height: 480px;
            border: 4px solid #2b2f38;
            border-radius: 6px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            display: grid;
            grid-template-columns: repeat(8, 1fr);
            grid-template-rows: repeat(8, 1fr);
        }}
        .square {{
            width: 60px;
            height: 60px;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: pointer;
        }}
        .light {{ background-color: {light_sq}; }}
        .dark {{ background-color: {dark_sq}; }}
        .selected {{ background-color: rgba(255, 255, 51, 0.55) !important; }}
        .last-move {{ background-color: rgba(205, 210, 106, 0.65) !important; }}
        .in-check {{
            background: radial-gradient(circle, rgba(255,0,0,0.85) 0%, rgba(255,0,0,0.3) 65%, transparent 100%) !important;
        }}
        .piece-img {{
            width: 52px;
            height: 52px;
            z-index: 2;
            transition: transform 0.08s ease;
            pointer-events: none;
        }}
        .square:hover .piece-img {{
            transform: scale(1.06);
        }}
        .hint-dot {{
            width: 18px;
            height: 18px;
            background: rgba(0, 0, 0, 0.22);
            border-radius: 50%;
            z-index: 3;
            pointer-events: none;
        }}
        .hint-capture {{
            width: 52px;
            height: 52px;
            border: 5px solid rgba(0, 0, 0, 0.25);
            border-radius: 50%;
            position: absolute;
            z-index: 3;
            pointer-events: none;
            box-sizing: border-box;
        }}
        .coord-rank {{
            position: absolute;
            top: 2px;
            left: 3px;
            font-size: 10px;
            font-weight: 700;
            opacity: 0.75;
        }}
        .coord-file {{
            position: absolute;
            bottom: 1px;
            right: 3px;
            font-size: 10px;
            font-weight: 700;
            opacity: 0.75;
        }}
        #promo-overlay {{
            display: none;
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.75);
            z-index: 10;
            justify-content: center;
            align-items: center;
            gap: 12px;
        }}
        .promo-btn {{
            background: #fff;
            border-radius: 8px;
            padding: 8px;
            cursor: pointer;
            border: 2px solid #81b64c;
        }}
        .promo-btn:hover {{ transform: scale(1.1); }}
    </style>
    </head>
    <body>
        <div id="board-wrapper">
            <div id="promo-overlay"></div>
        </div>

        <script>
            // Streamlit Component Communication Bridge
            function sendMessageToStreamlitClient(type, data) {{
                const outData = Object.assign({{ isStreamlitMessage: true, type: type }}, data);
                window.parent.postMessage(outData, "*");
            }}
            function initStreamlit() {{
                sendMessageToStreamlitClient("streamlit:componentReady", {{ apiVersion: 1 }});
                sendMessageToStreamlitClient("streamlit:setFrameHeight", {{ height: 500 }});
            }}
            function submitMove(uci) {{
                sendMessageToStreamlitClient("streamlit:setComponentValue", {{ value: uci }});
            }}

            // Web Audio Synthesizer for Crisp Chess Sounds
            const soundEvent = "{sound_event}";
            const moveCount = {move_count};
            function playSound(type) {{
                if (type === "none") return;
                const lastPlayed = sessionStorage.getItem("last_sound_move");
                if (lastPlayed == String(moveCount)) return;
                sessionStorage.setItem("last_sound_move", String(moveCount));

                try {{
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);

                    if (type === "move") {{
                        osc.type = "triangle";
                        osc.frequency.setValueAtTime(160, ctx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(60, ctx.currentTime + 0.08);
                        gain.gain.setValueAtTime(0.3, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);
                        osc.start(); osc.stop(ctx.currentTime + 0.08);
                    }} else if (type === "check") {{
                        osc.type = "sawtooth";
                        osc.frequency.setValueAtTime(440, ctx.currentTime);
                        osc.frequency.setValueAtTime(580, ctx.currentTime + 0.09);
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

            // Cburnett Wikimedia SVG Pieces
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

                const validTargets = selectedSq
                    ? legalMoves.filter(m => m.startsWith(selectedSq)).map(m => m.slice(2, 4))
                    : [];

                for (let r = 0; r < 8; r++) {{
                    for (let c = 0; c < 8; c++) {{
                        const sqName = files[c] + ranks[r];
                        const fileIdx = files[c].charCodeAt(0) - 97;
                        const rankIdx = parseInt(ranks[r]) - 1;
                        const isLight = (fileIdx + rankIdx) % 2 !== 0;

                        const sqDiv = document.createElement("div");
                        sqDiv.className = "square " + (isLight ? "light" : "dark");

                        if (lastMove && (lastMove.slice(0,2) === sqName || lastMove.slice(2,4) === sqName)) {{
                            sqDiv.classList.add("last-move");
                        }}
                        if (sqName === checkSq) {{
                            sqDiv.classList.add("in-check");
                        }}
                        if (sqName === selectedSq) {{
                            sqDiv.classList.add("selected");
                        }}

                        // Coordinates
                        if (c === 0) {{
                            const rSpan = document.createElement("span");
                            rSpan.className = "coord-rank";
                            rSpan.style.color = isLight ? "{dark_sq}" : "{light_sq}";
                            rSpan.innerText = ranks[r];
                            sqDiv.appendChild(rSpan);
                        }}
                        if (r === 7) {{
                            const fSpan = document.createElement("span");
                            fSpan.className = "coord-file";
                            fSpan.style.color = isLight ? "{dark_sq}" : "{light_sq}";
                            fSpan.innerText = files[c];
                            sqDiv.appendChild(fSpan);
                        }}

                        // Piece rendering
                        if (boardMap[sqName]) {{
                            const img = document.createElement("img");
                            img.src = PIECE_URLS[boardMap[sqName]];
                            img.className = "piece-img";
                            sqDiv.appendChild(img);
                        }}

                        // Move Hints
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
                    const matchingMoves = legalMoves.filter(m => m.startsWith(selectedSq + sq));
                    if (matchingMoves.length > 0) {{
                        // Check if pawn promotion (length 5 e.g. e7e8q)
                        if (matchingMoves[0].length === 5) {{
                            showPromotionPicker(selectedSq, sq);
                        }} else {{
                            submitMove(matchingMoves[0]);
                        }}
                        selectedSq = null;
                        render();
                        return;
                    }}
                }}

                if (boardMap[sq] && boardMap[sq].startsWith(turnColor)) {{
                    selectedSq = (selectedSq === sq) ? null : sq;
                }} else {{
                    selectedSq = null;
                }}
                render();
            }}

            function showPromotionPicker(fromSq, toSq) {{
                const overlay = document.getElementById("promo-overlay");
                overlay.innerHTML = "";
                overlay.style.display = "flex";
                ['q', 'r', 'b', 'n'].forEach(p => {{
                    const btn = document.createElement("div");
                    btn.className = "promo-btn";
                    const img = document.createElement("img");
                    img.src = PIECE_URLS[turnColor + p.toUpperCase()];
                    img.style.width = "48px";
                    img.style.height = "48px";
                    btn.appendChild(img);
                    btn.onclick = (e) => {{
                        e.stopPropagation();
                        overlay.style.display = "none";
                        submitMove(fromSq + toSq + p);
                    }};
                    overlay.appendChild(btn);
                }});
            }}

            initStreamlit();
            render();
            playSound(soundEvent);
        </script>
    </body>
    </html>
    """
    return components.html(html_code, height=500)

# ==========================================
# 5. Session State Initialization
# ==========================================
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "room_code" not in st.session_state:
    st.session_state.room_code = None
if "role" not in st.session_state:
    st.session_state.role = None
if "last_processed_uci" not in st.session_state:
    st.session_state.last_processed_uci = ""
if "board_theme" not in st.session_state:
    st.session_state.board_theme = "Tournament Green"

# ==========================================
# 6. Lobby Screen
# ==========================================
if not st.session_state.room_code:
    st.title("♚ Grandmaster Live Chess")
    st.caption("Real-time multiplayer chess with click-to-move board, live clocks, and sound effects.")

    with st.container(border=True):
        name_input = st.text_input("Your Nickname", value=st.session_state.player_name, placeholder="Enter your handle...")
        
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.subheader("Host a Match")
            tc_choice = st.selectbox(
                "Time Control",
                options=[
                    ("Rapid 10+0", 600, 0),
                    ("Blitz 3+2", 180, 2),
                    ("Bullet 1+0", 60, 0),
                    ("Unlimited (No Clock)", 0, 0)
                ],
                format_func=lambda x: x[0]
            )
            if st.button("➕ Create Room", type="primary", use_container_width=True):
                if not name_input.strip():
                    st.warning("Enter a nickname first.")
                else:
                    st.session_state.player_name = name_input.strip()
                    code = create_game(st.session_state.player_name, tc_choice[1], tc_choice[2])
                    st.session_state.room_code = code
                    st.session_state.role = "white"
                    st.session_state.last_processed_uci = ""
                    st.rerun()

        with col2:
            st.subheader("Join a Match")
            code_input = st.text_input("Room Code", placeholder="e.g. A7X9K").upper().strip()
            st.write("")
            st.write("")
            if st.button("🚪 Join Room", use_container_width=True):
                if not name_input.strip() or not code_input:
                    st.warning("Enter both a nickname and a room code.")
                else:
                    role, err = join_game(code_input, name_input.strip())
                    if err:
                        st.error(err)
                    else:
                        st.session_state.player_name = name_input.strip()
                        st.session_state.room_code = code_input
                        st.session_state.role = role
                        st.session_state.last_processed_uci = ""
                        st.rerun()

# ==========================================
# 7. Active Game Room
# ==========================================
else:
    with st.sidebar:
        st.header("Match Control")
        st.code(st.session_state.room_code, language=None)
        st.caption("Share this Room Code with your opponent.")
        st.write(f"**Player:** {st.session_state.player_name}")
        st.write(f"**Side:** {st.session_state.role.capitalize()}")

        st.divider()
        st.session_state.board_theme = st.selectbox("Board Theme", list(THEMES.keys()))

        st.divider()
        if st.session_state.role in ["white", "black"]:
            col_res, col_drw = st.columns(2)
            with col_res:
                if st.button("🏳️ Resign", use_container_width=True):
                    winner = "Black" if st.session_state.role == "white" else "White"
                    finish_game(st.session_state.room_code, f"{st.session_state.role.capitalize()} resigned. {winner} wins!")
                    st.rerun()
            with col_drw:
                if st.button("🤝 Offer Draw", use_container_width=True):
                    set_draw_offer(st.session_state.room_code, st.session_state.role)
                    st.rerun()

        if st.button("🔄 Rematch / Reset", use_container_width=True):
            st.session_state.last_processed_uci = ""
            reset_game(st.session_state.room_code)
            st.rerun()

        if st.button("⬅️ Leave Room", use_container_width=True):
            st.session_state.room_code = None
            st.session_state.role = None
            st.rerun()

    @st.fragment(run_every=1)
    def live_arena():
        game = get_game(st.session_state.room_code)
        if not game:
            st.error("Room closed.")
            return

        board = chess.Board(game["fen"])
        now = time.time()

        # Live clock calculation
        w_time = game["white_time"]
        b_time = game["black_time"]
        has_clock = game["time_control"] > 0

        if has_clock and game["status"] == "active" and game["last_tick"] > 0:
            elapsed = now - game["last_tick"]
            if board.turn == chess.WHITE:
                w_time = max(0.0, w_time - elapsed)
                if w_time == 0:
                    finish_game(st.session_state.room_code, "Black wins on time!")
                    st.rerun()
            else:
                b_time = max(0.0, b_time - elapsed)
                if b_time == 0:
                    finish_game(st.session_state.room_code, "White wins on time!")
                    st.rerun()

        # Draw offer banner
        if game["draw_offer"] and game["status"] == "active":
            opponent_role = "black" if game["draw_offer"] == "white" else "white"
            if st.session_state.role == opponent_role:
                st.warning(f"🤝 {game['draw_offer'].capitalize()} offered a draw!")
                c_acc, c_dec = st.columns(2)
                if c_acc.button("✅ Accept Draw", use_container_width=True):
                    finish_game(st.session_state.room_code, "Draw by mutual agreement.")
                    st.rerun()
                if c_dec.button("❌ Decline", use_container_width=True):
                    set_draw_offer(st.session_state.room_code, "")
                    st.rerun()
            elif st.session_state.role == game["draw_offer"]:
                st.info("Draw offer sent. Waiting for opponent...")

        # Status Banner
        if game["status"] == "waiting":
            st.warning("⏳ Waiting for opponent to join using Room Code...")
        elif game["status"] == "finished":
            st.success(f"🏆 **Game Over:** {game['result_reason']}")

        cap_by_w, cap_by_b, mat_diff = get_material_info(board)
        flipped = (st.session_state.role == "black")

        top_player = game["white_player"] if flipped else (game["black_player"] or "Waiting...")
        bot_player = (game["black_player"] or "Waiting...") if flipped else game["white_player"]
        top_time = w_time if flipped else b_time
        bot_time = b_time if flipped else w_time
        top_cap = cap_by_w if flipped else cap_by_b
        bot_cap = cap_by_b if flipped else cap_by_w
        top_adv = f"+{mat_diff}" if (flipped and mat_diff > 0) else (f"+{-mat_diff}" if (not flipped and mat_diff < 0) else "")
        bot_adv = f"+{-mat_diff}" if (flipped and mat_diff < 0) else (f"+{mat_diff}" if (not flipped and mat_diff > 0) else "")
        top_active = (board.turn == chess.WHITE) if flipped else (board.turn == chess.BLACK)
        bot_active = not top_active

        col_board, col_side = st.columns([1.35, 1], gap="large")

        with col_board:
            # Top Player Card
            top_clock_cls = "running" if (top_active and game["status"] == "active") else ""
            if has_clock and top_time < 20:
                top_clock_cls = "low-time"
            top_clock_html = f'<div class="clock-box {top_clock_cls}">{format_clock(top_time)}</div>' if has_clock else ""
            top_adv_html = f'<span class="adv-badge">{top_adv}</span>' if top_adv else ""
            st.markdown(f"""
                <div class="player-card {'active-turn' if top_active else ''}">
                    <div>
                        <strong>{'⚪' if flipped else '⚫'} {top_player}</strong>{top_adv_html}
                        <div class="captured-row">{top_cap}</div>
                    </div>
                    {top_clock_html}
                </div>
            """, unsafe_allow_html=True)

            # Interactive Board
            is_my_turn = (
                game["status"] == "active"
                and (
                    (board.turn == chess.WHITE and st.session_state.role == "white")
                    or (board.turn == chess.BLACK and st.session_state.role == "black")
                )
            )
            move_count = len(game["pgn_moves"].split())
            clicked_uci = interactive_chessboard(
                board=board,
                flipped=flipped,
                can_move=is_my_turn,
                last_move_uci=game["last_move_uci"],
                theme_colors=THEMES[st.session_state.board_theme],
                move_count=move_count
            )

            if clicked_uci and isinstance(clicked_uci, str) and clicked_uci != st.session_state.last_processed_uci:
                st.session_state.last_processed_uci = clicked_uci
                apply_move_db(st.session_state.room_code, clicked_uci)
                st.rerun()

            # Bottom Player Card
            bot_clock_cls = "running" if (bot_active and game["status"] == "active") else ""
            if has_clock and bot_time < 20:
                bot_clock_cls = "low-time"
            bot_clock_html = f'<div class="clock-box {bot_clock_cls}">{format_clock(bot_time)}</div>' if has_clock else ""
            bot_adv_html = f'<span class="adv-badge">{bot_adv}</span>' if bot_adv else ""
            st.markdown(f"""
                <div class="player-card {'active-turn' if bot_active else ''}">
                    <div>
                        <strong>{'⚫' if flipped else '⚪'} {bot_player}</strong>{bot_adv_html}
                        <div class="captured-row">{bot_cap}</div>
                    </div>
                    {bot_clock_html}
                </div>
            """, unsafe_allow_html=True)

        with col_side:
            tab_moves, tab_chat = st.tabs(["📜 Move Sheet", "💬 Live Chat"])

            with tab_moves:
                moves = game["pgn_moves"].split()
                if moves:
                    rows_md = "| # | White | Black |\n|---|---|---|\n"
                    for i in range(0, len(moves), 2):
                        num = (i // 2) + 1
                        w_m = moves[i]
                        b_m = moves[i + 1] if i + 1 < len(moves) else ""
                        rows_md += f"| {num}. | **{w_m}** | **{b_m}** |\n"
                    st.markdown(rows_md)
                    st.download_button(
                        "⬇️ Download PGN",
                        data=game["pgn_moves"],
                        file_name=f"match_{st.session_state.room_code}.pgn",
                        use_container_width=True
                    )
                else:
                    st.caption("Click a piece on the board to make the first move.")

            with tab_chat:
                logs = json.loads(game["chat_log"])
                chat_box = st.container(height=280)
                with chat_box:
                    if not logs:
                        st.caption("No messages yet. Say GLHF!")
                    for entry in logs:
                        st.markdown(f"**{entry['sender']}:** {entry['text']}")

                with st.form("chat_form", clear_on_submit=True):
                    c_in, c_btn = st.columns([4, 1])
                    msg = c_in.text_input("Message", label_visibility="collapsed", placeholder="Type message...")
                    if c_btn.form_submit_button("Send") and msg.strip():
                        send_chat(st.session_state.room_code, st.session_state.player_name, msg.strip())
                        st.rerun()

    live_arena()