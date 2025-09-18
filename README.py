import sys
import os
import datetime
import pygame
import chess
from pygame import Rect

# ---------------------------- Config ----------------------------
BOARD_SIZE = 8
SQUARE_SIZE = 72          # Big squares (try 96, 120, 144)
OUTER_MARGIN = 40           # Space around the board for labels
LABEL_GAP = 28              # Space for file/rank labels
BORDER_RADIUS = 18

# Colors
BG      = (24, 24, 28)      # window background
BORDER  = (70, 70, 80)      # outer border frame
LIGHT   = (240, 217, 181)   # light square
DARK    = (181, 136, 99)    # dark square
HILITE  = (246, 246, 105)   # selection/hover
LASTMV  = (255, 244, 180)   # last-move highlight
CHECK   = (255, 120, 120)   # check highlight
DOT     = (40, 40, 40)      # legal move dot (for empty targets)
RING    = (20, 20, 20)      # capture target ring

FILES = "abcdefgh"
RANKS = "12345678"

GLYPHS = {
    chess.KING:   ('♔', '♚'),
    chess.QUEEN:  ('♕', '♛'),
    chess.ROOK:   ('♖', '♜'),
    chess.BISHOP: ('♗', '♝'),
    chess.KNIGHT: ('♘', '♞'),
    chess.PAWN:   ('♙', '♟'),
}

FONT_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf"),
    'DejaVuSans',
    'Noto Sans Symbols 2',
    'Noto Sans Symbols',
    'Arial Unicode MS',
    'Segoe UI Symbol',
    'Symbola',
]

# Derived sizes
BOARD_PIX = BOARD_SIZE * SQUARE_SIZE
WIN_W = OUTER_MARGIN*2 + BOARD_PIX
WIN_H = OUTER_MARGIN*2 + LABEL_GAP + BOARD_PIX

# ---------------------------- Utility ----------------------------

def find_font(px: int) -> pygame.font.Font:
    """Pick a font that supports chess glyphs if available."""
    pygame.font.init()
    for name in FONT_CANDIDATES:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, px)
    return pygame.font.SysFont(None, px)

def model_to_display(sq: int, flipped: bool):
    """Convert python-chess square -> (row, col) on the screen grid."""
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    if not flipped:
        r = 7 - rank
        c = file
    else:
        r = rank
        c = 7 - file
    return r, c

def display_to_model(r: int, c: int, flipped: bool):
    """Convert screen grid (row, col) -> python-chess square index, or None if invalid."""
    if not (0 <= r < 8 and 0 <= c < 8):
        return None
    if not flipped:
        file = c
        rank = 7 - r
    else:
        file = 7 - c
        rank = r
    return chess.square(file, rank)

def square_at_pixel(pos):
    """Mouse pixel -> (row, col) grid or None if outside board."""
    x, y = pos
    bx = x - OUTER_MARGIN
    by = y - OUTER_MARGIN
    if 0 <= bx < BOARD_PIX and 0 <= by < BOARD_PIX:
        col = bx // SQUARE_SIZE
        row = by // SQUARE_SIZE
        return int(row), int(col)
    return None

def legal_moves_from(board: chess.Board, src: int):
    """Return list of legal moves from src square."""
    return [m for m in board.legal_moves if m.from_square == src]

def move_for(board: chess.Board, src: int, dst: int, promotion: int | None = None):
    """Find a legal move object matching src->dst (and promotion if necessary)."""
    for m in board.legal_moves:
        if m.from_square == src and m.to_square == dst:
            if chess.Move.from_uci(m.uci()).promotion == promotion or m.promotion == promotion:
                return m
    return None

def needs_promotion(board: chess.Board, src: int, dst: int) -> bool:
    """Check if moving from src to dst would require a promotion (pawn reaching last rank)."""
    piece = board.piece_at(src)
    if piece is None or piece.piece_type != chess.PAWN:
        return False
    rank = chess.square_rank(dst)
    return rank == 0 or rank == 7

def save_screenshot(screen: pygame.Surface):
    os.makedirs("screens", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("screens", f"chess_{ts}.png")
    pygame.image.save(screen, path)
    print(f"Saved {path}")

# ---------------------------- Drawing ----------------------------

def draw_board(surface, label_font, flipped, last_move=None, check_sq=None):
    surface.fill(BG)

    # Frame
    frame_rect = Rect(OUTER_MARGIN-8, OUTER_MARGIN-8, BOARD_PIX+16, BOARD_PIX+16)
    pygame.draw.rect(surface, BORDER, frame_rect, border_radius=BORDER_RADIUS)

    # Squares
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r + c) % 2 == 0 else DARK
            rect = Rect(OUTER_MARGIN + c*SQUARE_SIZE, OUTER_MARGIN + r*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(surface, color, rect, border_radius=10)

    # Last move highlight
    if last_move:
        for sq in (last_move.from_square, last_move.to_square):
            rr, cc = model_to_display(sq, flipped)
            rect = Rect(OUTER_MARGIN + cc*SQUARE_SIZE, OUTER_MARGIN + rr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            s.fill((*LASTMV, 90))
            surface.blit(s, rect.topleft)

    # Check square highlight
    if check_sq is not None:
        rr, cc = model_to_display(check_sq, flipped)
        rect = Rect(OUTER_MARGIN + cc*SQUARE_SIZE, OUTER_MARGIN + rr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        s.fill((*CHECK, 110))
        surface.blit(s, rect.topleft)

    # File labels (bottom)
    for i in range(8):
        file_char = FILES[::-1][i] if flipped else FILES[i]
        label = label_font.render(file_char, True, (230, 230, 230))
        lx = OUTER_MARGIN + i*SQUARE_SIZE + SQUARE_SIZE//2 - label.get_width()//2
        ly = OUTER_MARGIN + BOARD_PIX + 6
        surface.blit(label, (lx, ly))

    # Rank labels (left)
    for i in range(8):
        rank_char = RANKS[i] if flipped else RANKS[::-1][i]
        label = label_font.render(rank_char, True, (230, 230, 230))
        lx = OUTER_MARGIN - 12 - label.get_width()
        ly = OUTER_MARGIN + i*SQUARE_SIZE + SQUARE_SIZE//2 - label.get_height()//2
        surface.blit(label, (lx, ly))

def draw_pieces(surface, board: chess.Board, piece_font, flipped, skip_sq=None, drag_pos=None, glyph_shadow=True):
    """Draw all pieces; optionally skip a square (the one being dragged) and draw it at drag_pos."""
    for sq in chess.SQUARES:
        if sq == skip_sq:
            continue
        piece = board.piece_at(sq)
        if not piece:
            continue
        draw_piece_on_sq(surface, piece, sq, piece_font, flipped, glyph_shadow)

    # Dragged piece on top
    if skip_sq is not None and drag_pos is not None:
        piece = board.piece_at(skip_sq)
        if piece:
            draw_piece_at(surface, piece, drag_pos, piece_font, glyph_shadow)

def draw_piece_on_sq(surface, piece: chess.Piece, sq: int, piece_font, flipped, glyph_shadow=True):
    r, c = model_to_display(sq, flipped)
    cx = OUTER_MARGIN + c*SQUARE_SIZE + SQUARE_SIZE//2
    cy = OUTER_MARGIN + r*SQUARE_SIZE + SQUARE_SIZE//2
    draw_glyph(surface, piece, (cx, cy), piece_font, glyph_shadow)

def draw_piece_at(surface, piece: chess.Piece, pos_xy, piece_font, glyph_shadow=True):
    cx, cy = pos_xy
    draw_glyph(surface, piece, (cx, cy), piece_font, glyph_shadow)

def draw_glyph(surface, piece: chess.Piece, center_xy, piece_font, glyph_shadow=True):
    white = piece.color
    glyph = GLYPHS[piece.piece_type][0 if white else 1]
    # Slight outline/shadow
    if glyph_shadow:
        surf_shadow = piece_font.render(glyph, True, (0, 0, 0))
        surface.blit(surf_shadow, (center_xy[0] - surf_shadow.get_width()//2 + 3,
                                   center_xy[1] - surf_shadow.get_height()//2 + 3))
    surf = piece_font.render(glyph, True, (255, 255, 255))
    surface.blit(surf, (center_xy[0] - surf.get_width()//2,
                        center_xy[1] - surf.get_height()//2))

def draw_move_hints(surface, board: chess.Board, src: int, legal_from_src, flipped):
    """Draw dots/rings for legal targets from src."""
    for m in legal_from_src:
        rr, cc = model_to_display(m.to_square, flipped)
        rect = Rect(OUTER_MARGIN + cc*SQUARE_SIZE, OUTER_MARGIN + rr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        target_piece = board.piece_at(m.to_square)
        cx = rect.centerx
        cy = rect.centery
        if target_piece is None:
            # Dot for empty target
            pygame.draw.circle(surface, DOT, (cx, cy), SQUARE_SIZE//10)
        else:
            # Ring for capture
            pygame.draw.circle(surface, RING, (cx, cy), SQUARE_SIZE//2 - 8, width=6)

def draw_promotion_overlay(surface, piece_font, label_font, white_to_move: bool):
    """Simple centered overlay to choose promotion piece by click or key."""
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    overlay.fill((10, 10, 10, 170))
    panel_w = SQUARE_SIZE*4 + 48
    panel_h = SQUARE_SIZE + 64
    panel = Rect((WIN_W - panel_w)//2, (WIN_H - panel_h)//2, panel_w, panel_h)
    pygame.draw.rect(overlay, (230, 230, 230), panel, border_radius=14)

    # Title
    title = label_font.render("Choose promotion: Q  R  B  N", True, (20, 20, 20))
    overlay.blit(title, (panel.centerx - title.get_width()//2, panel.top + 10))

    # Four piece boxes
    pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    boxes = []
    for i, ptype in enumerate(pieces):
        x = panel.left + 24 + i*(SQUARE_SIZE + 16)
        y = panel.top + 36
        rect = Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)
        pygame.draw.rect(overlay, (245, 245, 245), rect, border_radius=10)
        glyph = GLYPHS[ptype][0 if white_to_move else 1]
        glyph_surf = piece_font.render(glyph, True, (0,0,0))
        overlay.blit(glyph_surf, (rect.centerx - glyph_surf.get_width()//2 + 2,
                                  rect.centery - glyph_surf.get_height()//2 + 2))
        glyph_surf2 = piece_font.render(glyph, True, (255,255,255))
        overlay.blit(glyph_surf2, (rect.centerx - glyph_surf2.get_width()//2,
                                   rect.centery - glyph_surf2.get_height()//2))
        boxes.append((rect, ptype))

    surface.blit(overlay, (0, 0))
    return boxes  # list of (rect, piece_type)

# ---------------------------- Main ----------------------------

def main():
    pygame.init()
    pygame.display.set_caption("Big Chess — Pygame + python-chess")
    screen = pygame.display.set_mode((WIN_W, WIN_H))

    # Fonts
    piece_font = find_font(int(SQUARE_SIZE * 0.80))
    label_font = find_font(22)

    board = chess.Board()
    flipped = False
    show_hints = True

    dragging = {
        'active': False,     # currently dragging
        'sq': None,          # source square
        'pos': (0, 0),       # current mouse pos
        'moves': [],         # legal moves from source
    }

    promotion_state = {
        'pending': False,
        'src': None,
        'dst': None,
    }

    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(60)
        last_move = board.peek() if board.move_stack else None
        check_sq = None
        if board.is_check():
            # side to move is in check
            king_sq = board.king(board.turn)
            if king_sq is not None:
                check_sq = king_sq

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_f:
                    flipped = not flipped
                elif event.key == pygame.K_u:
                    if board.move_stack:
                        board.pop()
                elif event.key == pygame.K_r:
                    board.reset()
                elif event.key == pygame.K_s:
                    save_screenshot(screen)
                elif event.key == pygame.K_h:
                    show_hints = not show_hints
                # Promotion via hotkeys if dialog is open
                elif promotion_state['pending']:
                    key_map = {
                        pygame.K_q: chess.QUEEN,
                        pygame.K_r: chess.ROOK,
                        pygame.K_b: chess.BISHOP,
                        pygame.K_n: chess.KNIGHT,
                    }
                    if event.key in key_map:
                        ptype = key_map[event.key]
                        src, dst = promotion_state['src'], promotion_state['dst']
                        m = move_for(board, src, dst, promotion=ptype)
                        if m:
                            board.push(m)
                        promotion_state.update({'pending': False, 'src': None, 'dst': None})

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not promotion_state['pending']:
                grid = square_at_pixel(event.pos)
                if grid:
                    r, c = grid
                    sq = display_to_model(r, c, flipped)
                    if sq is None:
                        continue
                    piece = board.piece_at(sq)
                    if piece and piece.color == board.turn:
                        dragging['active'] = True
                        dragging['sq'] = sq
                        dragging['pos'] = event.pos
                        dragging['moves'] = legal_moves_from(board, sq)

            elif event.type == pygame.MOUSEMOTION and dragging['active']:
                dragging['pos'] = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging['active'] and not promotion_state['pending']:
                    grid = square_at_pixel(event.pos)
                    src = dragging['sq']
                    if grid and src is not None:
                        r, c = grid
                        dst = display_to_model(r, c, flipped)
                        # Handle promotions
                        if needs_promotion(board, src, dst):
                            # Offer dialog (only if some promotion move is legal)
                            possible = any(m.from_square == src and m.to_square == dst and m.promotion for m in board.legal_moves)
                            if possible:
                                promotion_state.update({'pending': True, 'src': src, 'dst': dst})
                            else:
                                # no legal promotion to this square
                                pass
                        else:
                            m = move_for(board, src, dst, promotion=None)
                            if m:
                                board.push(m)
                    # reset drag
                    dragging['active'] = False
                    dragging['sq'] = None
                    dragging['pos'] = (0, 0)
                    dragging['moves'] = []

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and promotion_state['pending']:
                # Click on promotion panel
                boxes = draw_promotion_overlay(screen, piece_font, label_font, board.turn)
                # detect clicks
                mouse = pygame.mouse.get_pos()
                for rect, ptype in boxes:
                    if rect.collidepoint(mouse):
                        src, dst = promotion_state['src'], promotion_state['dst']
                        m = move_for(board, src, dst, promotion=ptype)
                        if m:
                            board.push(m)
                        promotion_state.update({'pending': False, 'src': None, 'dst': None})
                        break

        # ---------- Rendering ----------
        draw_board(screen, label_font, flipped, last_move=last_move, check_sq=check_sq)

        # Selected/drag square highlight
        if dragging['active'] and dragging['sq'] is not None:
            rr, cc = model_to_display(dragging['sq'], flipped)
            rect = Rect(OUTER_MARGIN + cc*SQUARE_SIZE, OUTER_MARGIN + rr*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            s.fill((*HILITE, 80))
            screen.blit(s, rect.topleft)

        # Move hints
        if show_hints and dragging['active'] and dragging['moves']:
            draw_move_hints(screen, board, dragging['sq'], dragging['moves'], flipped)

        # Pieces (skip dragged square and draw that glyph at cursor)
        skip = dragging['sq'] if dragging['active'] else None
        drag_xy = dragging['pos'] if dragging['active'] else None
        draw_pieces(screen, board, piece_font, flipped, skip_sq=skip, drag_pos=drag_xy)

        # Promotion overlay (draw on top, but don't block event loop visuals)
        if promotion_state['pending']:
            draw_promotion_overlay(screen, piece_font, label_font, board.turn)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        pygame.quit()
        sys.exit(1)