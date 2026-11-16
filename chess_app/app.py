import streamlit as st
import sqlite3
import chess
import chess.svg
import random
import string
import base64

st.set_page_config(page_title="Online Multiplayer Chess", page_icon="♟️", layout="wide")

# ==========================================
# 1. Database Setup (SQLite)
# ==========================================
DB_FILE = "chess_games.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS games (
            room_code TEXT PRIMARY KEY,
            fen TEXT NOT NULL,
            pgn_moves TEXT DEFAULT '',
            white_player TEXT,
            black_player TEXT,
            status TEXT DEFAULT 'waiting'
        )
    """)
    conn.commit()
    conn.close()

def generate_room_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def create_game(player_name):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    room_code = generate_room_code()
    initial_fen = chess.Board().fen()
    c.execute(
        "INSERT INTO games (room_code, fen, pgn_moves, white_player, black_player, status) VALUES (?, ?, '', ?, NULL, 'waiting')",
        (room_code, initial_fen, player_name)
    )
    conn.commit()
    conn.close()
    return room_code

def join_game(room_code, player_name):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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
        c.execute("UPDATE games SET black_player = ?, status = 'active' WHERE room_code = ?", (player_name, room_code))
        conn.commit()
        conn.close()
        return "black", None
    
    conn.close()
    return "spectator", None

def get_game(room_code):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT fen, pgn_moves, white_player, black_player, status FROM games WHERE room_code = ?", (room_code,))
    row = c.fetchone()
    conn.close()
    return row

def update_game_state(room_code, new_fen, new_pgn, new_status):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        "UPDATE games SET fen = ?, pgn_moves = ?, status = ? WHERE room_code = ?",
        (new_fen, new_pgn, new_status, room_code)
    )
    conn.commit()
    conn.close()

def reset_game(room_code):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    initial_fen = chess.Board().fen()
    c.execute(
        "UPDATE games SET fen = ?, pgn_moves = '', status = 'active' WHERE room_code = ?",
        (initial_fen, room_code)
    )
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. Session State
# ==========================================
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "room_code" not in st.session_state:
    st.session_state.room_code = None
if "role" not in st.session_state:
    st.session_state.role = None  # 'white', 'black', or 'spectator'

# ==========================================
# 3. Helper: Render SVG Board
# ==========================================
def render_board(board, flipped=False, last_move=None):
    svg = chess.svg.board(
        board=board,
        flipped=flipped,
        lastmove=last_move,
        check=board.king(board.turn) if board.is_check() else None,
        size=520
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    st.markdown(
        f'<div style="display:flex; justify-content:center;"><img src="data:image/svg+xml;base64,{b64}"/></div>',
        unsafe_allow_html=True
    )

# ==========================================
# 4. Lobby Screen
# ==========================================
if not st.session_state.room_code:
    st.title("♟️ Online Multiplayer Chess")
    st.write("Create a room and share the Room Code with a friend to play live.")

    with st.container(border=True):
        name_input = st.text_input("Your Nickname", value=st.session_state.player_name, placeholder="e.g. Youssef")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Host a New Game")
            if st.button("➕ Create Room", use_container_width=True):
                if not name_input.strip():
                    st.warning("Enter a nickname first.")
                else:
                    st.session_state.player_name = name_input.strip()
                    code = create_game(st.session_state.player_name)
                    st.session_state.room_code = code
                    st.session_state.role = "white"
                    st.rerun()

        with col2:
            st.subheader("Join Existing Game")
            code_input = st.text_input("Room Code", placeholder="e.g. A7X9K").upper().strip()
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
                        st.rerun()

# ==========================================
# 5. Live Game Room (Auto-refreshes every 2s)
# ==========================================
else:
    with st.sidebar:
        st.header("Room Info")
        st.code(st.session_state.room_code, language=None)
        st.caption("Share this code with your opponent.")
        st.write(f"**You:** {st.session_state.player_name}")
        st.write(f"**Role:** {st.session_state.role.capitalize()}")
        
        st.divider()
        if st.button("🔄 Rematch / Reset Board", use_container_width=True):
            reset_game(st.session_state.room_code)
            st.rerun()
        if st.button("⬅️ Leave Room", use_container_width=True):
            st.session_state.room_code = None
            st.session_state.role = None
            st.rerun()

    @st.fragment(run_every=2)
    def live_game_view():
        game = get_game(st.session_state.room_code)
        if not game:
            st.error("Game room no longer exists.")
            return

        fen, pgn_moves, white_p, black_p, status = game
        board = chess.Board(fen)

        # Header Status Banner
        col_w, col_mid, col_b = st.columns([2, 3, 2])
        with col_w:
            st.info(f"⚪ **White:** {white_p}")
        with col_mid:
            if status == "waiting":
                st.warning("⏳ Waiting for Black player to join...")
            elif board.is_checkmate():
                winner = "Black" if board.turn == chess.WHITE else "White"
                st.success(f"🏆 Checkmate! {winner} wins!")
            elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
                st.warning("🤝 Game Drawn!")
            else:
                turn_str = "White's Turn" if board.turn == chess.WHITE else "Black's Turn"
                check_str = " (CHECK!)" if board.is_check() else ""
                st.subheader(f"🎯 {turn_str}{check_str}")
        with col_b:
            st.info(f"⚫ **Black:** {black_p if black_p else 'Waiting...'}")

        # Main Board & Controls Layout
        board_col, control_col = st.columns([1.4, 1], gap="large")

        with board_col:
            # Parse last move for highlighting if available
            last_move = None
            move_list = pgn_moves.split()
            if move_list:
                temp_board = chess.Board()
                for san in move_list:
                    try:
                        last_move = temp_board.parse_san(san)
                        temp_board.push(last_move)
                    except ValueError:
                        pass

            flipped = (st.session_state.role == "black")
            render_board(board, flipped=flipped, last_move=last_move)

        with control_col:
            st.subheader("Make a Move")
            
            is_white_turn = (board.turn == chess.WHITE)
            can_move = (
                not board.is_game_over()
                and (
                    (is_white_turn and st.session_state.role == "white")
                    or (not is_white_turn and st.session_state.role == "black")
                )
            )

            if st.session_state.role == "spectator":
                st.caption("You are spectating this match.")
            elif board.is_game_over():
                st.caption("Game over. Click 'Rematch / Reset Board' in the sidebar to play again.")
            elif not can_move:
                st.info("Waiting for opponent's move...")
            else:
                # Dropdown of all legal moves in clean Standard Algebraic Notation (e.g., Nf3, e4, O-O)
                legal_sans = sorted([board.san(m) for m in board.legal_moves])
                selected_san = st.selectbox(
                    "Select Legal Move (or type to search, e.g., e4, Nf3, O-O)",
                    options=legal_sans,
                    index=None,
                    placeholder="Choose your move..."
                )

                if st.button("✅ Play Move", type="primary", use_container_width=True):
                    if selected_san:
                        move = board.parse_san(selected_san)
                        board.push(move)
                        updated_pgn = (pgn_moves + " " + selected_san).strip()
                        new_status = "finished" if board.is_game_over() else "active"
                        update_game_state(st.session_state.room_code, board.fen(), updated_pgn, new_status)
                        st.rerun()
                    else:
                        st.warning("Select a move first.")

            st.divider()
            st.subheader("Move History")
            if pgn_moves:
                moves = pgn_moves.split()
                formatted_moves = []
                for i in range(0, len(moves), 2):
                    move_num = (i // 2) + 1
                    w_move = moves[i]
                    b_move = moves[i + 1] if i + 1 < len(moves) else ""
                    formatted_moves.append(f"{move_num}. {w_move} {b_move}")
                st.text_area("PGN", value="  |  ".join(formatted_moves), height=150, disabled=True)
            else:
                st.caption("No moves played yet.")

    live_game_view()