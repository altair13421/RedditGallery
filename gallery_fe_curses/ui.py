import curses


class ScrollableWindow:
    """
    A simple scrollable text window.
    """

    def __init__(self, win: curses.window):
        self.win = win                      # the underlying curses window
        self.content = []                   # list of strings
        self.offset = 0                     # first visible line

    def set_content(self, lines):
        """Replace all content."""
        self.content = lines[:]
        self.offset = 0
        self.refresh()

    def scroll_up(self, n=1):
        if self.offset > 0:
            self.offset = max(0, self.offset - n)
            self.refresh()

    def scroll_down(self, n=1):
        h, _ = self.win.getmaxyx()
        max_offset = max(0, len(self.content) - h)
        if self.offset < max_offset:
            self.offset = min(max_offset, self.offset + n)
            self.refresh()

    def refresh(self):
        """Redraw the visible part."""
        h, w = self.win.getmaxyx()
        self.win.erase()
        for i in range(h):
            line_idx = self.offset + i
            if line_idx >= len(self.content):
                break
            # clip to width and add a newline
            self.win.addnstr(i, 0, self.content[line_idx], w - 1)
        self.win.noutrefresh()


class PanelOne:
    """
    Left column. Two sub‑windows with a 5:3 vertical ratio.
    Both are ScrollableWindow instances.
    """

    def __init__(self, stdscr, x, y, width):
        self.win = curses.newwin(0, width, y, x)          # full height
        h, _ = self.win.getmaxyx()
        split = int(h * 5 / 8)

        self.top_win   = ScrollableWindow(
            curses.newwin(split, width, y, x))
        self.bottom_win = ScrollableWindow(
            curses.newwin(h - split, width, y + split, x))

    def set_top(self, lines):
        self.top_win.set_content(lines)

    def set_bottom(self, lines):
        self.bottom_win.set_content(lines)

    def handle_key(self, key):
        if key == curses.KEY_UP:
            self.top_win.scroll_up()
        elif key == curses.KEY_DOWN:
            self.top_win.scroll_down()

    def refresh(self):
        # nothing extra – sub‑windows already call noutrefresh
        pass


class PanelTwo:
    """
    Middle column – a single scrollable window.
    """

    def __init__(self, stdscr, x, y, width):
        self.win = curses.newwin(0, width, y, x)
        self.scr_win = ScrollableWindow(self.win)

    def set_content(self, lines):
        self.scr_win.set_content(lines)

    def handle_key(self, key):
        if key == curses.KEY_UP:
            self.scr_win.scroll_up()
        elif key == curses.KEY_DOWN:
            self.scr_win.scroll_down()

    def refresh(self):
        pass


class PanelThree:
    """
    Right column – two non‑scrollable windows with a 7:3 vertical ratio.
    """

    def __init__(self, stdscr, x, y, width):
        self.win = curses.newwin(0, width, y, x)
        h, _ = self.win.getmaxyx()
        split = int(h * 7 / 10)

        self.top_win   = curses.newwin(split, width, y, x)
        self.bottom_win = curses.newwin(h - split, width, y + split, x)

    def set_top(self, lines):
        self._draw_lines(self.top_win, lines)

    def set_bottom(self, lines):
        self._draw_lines(self.bottom_win, lines)

    @staticmethod
    def _draw_lines(win, lines):
        win.erase()
        h, w = win.getmaxyx()
        for i in range(min(h, len(lines))):
            win.addnstr(i, 0, lines[i], w - 1)
        win.noutrefresh()

    def handle_key(self, key):
        # no scrolling – ignore keys
        pass

    def refresh(self):
        pass

def main(stdscr):
    curses.curs_set(0)          # hide cursor
    stdscr.nodelay(True)        # non‑blocking getch
    stdscr.keypad(True)

    max_y, max_x = stdscr.getmaxyx()
    col_w = max_x // 3

    p1 = PanelOne(stdscr, 0, 0, col_w)
    p2 = PanelTwo(stdscr, col_w, 0, col_w)
    p3 = PanelThree(stdscr, 2 * col_w, 0, max_x - 2 * col_w)

    # demo data
    lines = [f"Line {i}" for i in range(1, 101)]
    p1.set_top(lines[:50])
    p1.set_bottom(lines[50:80])

    p2.set_content(lines)
    p3.set_top(["Top part of panel 3"])
    p3.set_bottom(["Bottom part of panel 3"])

    while True:
        key = stdscr.getch()
        if key == ord('q'):
            break

        # propagate keys to panels that care about them
        for pnl in (p1, p2, p3):
            pnl.handle_key(key)

        # refresh everything
        curses.doupdate()

curses.wrapper(main)

