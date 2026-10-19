package org.broccoli.controller;
interface IShell {
    String execute(String operation, String arguments);
    int uid();
    void destroy();
}
