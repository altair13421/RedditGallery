#pragma once

#include <ncurses.h>
#include <csignal>

namespace ui {

class NcursesApp {
public:
    void run();                     // public entry point

private:
    static void sigint_handler(int);   // signal handler

    void init();                      // ncurses bootstrap
    void cleanup();                   // restore terminal

    /* ----------  State ---------------------------------------------- */
    int y_ = LINES / 2;
    int x_ = COLS / 2;
    bool quit_{false};

    /* ----------  Static helper to let the handler reach this instance --------- */
    static NcursesApp* current_;      // set in init()
};

}   // namespace ui
