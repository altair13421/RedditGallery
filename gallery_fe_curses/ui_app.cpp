#include "ui_app.hpp"

namespace ui {

// --------------------------------------------------------------
// Definition of the static pointer (must be outside any function)
// --------------------------------------------------------------
NcursesApp* NcursesApp::current_ = nullptr;

// --------------------------------------------------------------
// Signal handler – set quit_ flag on the current instance.
// --------------------------------------------------------------
void NcursesApp::sigint_handler(int /*unused*/) {
    if (current_) current_->quit_ = true;
}

// --------------------------------------------------------------
// ncurses bootstrap
// --------------------------------------------------------------
void NcursesApp::init() {
    initscr();              // start curses mode
    cbreak();               // immediate input
    noecho();               // don't echo keys
    keypad(stdscr, TRUE);   // enable arrow keys, etc.
    curs_set(0);            // hide cursor

    current_ = this;        // make the handler aware of us
    std::signal(SIGINT, sigint_handler);  // Ctrl‑C → quit_
}

// --------------------------------------------------------------
// Restore terminal to normal state
// --------------------------------------------------------------
void NcursesApp::cleanup() {
    endwin();               // leave curses mode
    current_ = nullptr;     // clear global pointer
}

// --------------------------------------------------------------
// Main event loop – minimal, tight, fast.
// --------------------------------------------------------------
void NcursesApp::run() {
    init();

    const char *msg = "Arrow keys move the square. Press 'q' or Ctrl-C to quit.";
    mvprintw(0, 0, "%s", msg);
    refresh();

    while (!quit_) {
        // Draw current position
        mvaddch(y_, x_, 'O');
        refresh();

        int ch = getch();           // blocking read

        // Erase old character
        mvaddch(y_, x_, ' ');
        switch (ch) {
            case KEY_UP:    --y_; break;
            case KEY_DOWN:  ++y_; break;
            case KEY_LEFT:  --x_; break;
            case KEY_RIGHT: ++x_; break;
            case 'q':
            case 'Q':      quit_ = true; break;
            default: /* ignore */ ;
        }

        // Clamp to screen bounds
        if (y_ < 1) y_ = 1;
        if (y_ >= LINES) y_ = LINES - 1;
        if (x_ < 0) x_ = 0;
        if (x_ >= COLS) x_ = COLS - 1;
    }

    cleanup();
}

}   // namespace ui
