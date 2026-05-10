# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A standalone Pomodoro timer app — a single HTML file with embedded CSS and JavaScript. Zero dependencies, runs in any modern browser by opening `pomodoro.html` directly.

## Architecture

The entire app is in one file (`pomodoro.html`) with three inline sections:

- **CSS** (`<style>`): Dark-theme UI with a circular progress ring (SVG), tab navigation (focus/break), settings inputs, and responsive layout.
- **HTML**: The DOM structure — timer ring, display, control buttons (start/pause/reset), mode tabs, duration settings, session counter.
- **JavaScript** (bottom of `<script>`): All app logic — timer state management (`setInterval`-based countdown), circular progress ring animation (SVG `stroke-dashoffset`), mode switching (work/short break/long break), notification sounds (Web Audio API), settings persistence via `localStorage`, keyboard shortcuts (Space=toggle, R=reset).

## Key Design Details

- **Timer ring**: SVG `<circle>` with `stroke-dasharray`/`stroke-dashoffset` for the progress animation. Circumference is hardcoded as `2 * π * 115`.
- **Auto-switch**: After a work session, auto-advances to short break (or long break every 4th session). After break, returns to work mode.
- **Persistence**: Session count is saved to `localStorage` under key `pomodoroSessions`.
- **Notifications**: Uses `AudioContext` / Web Audio API to generate three ascending tones (no external audio files needed).
- **Constraints**: Duration inputs are clamped to min/max attributes; tab switching is disabled while timer is running; keyboard shortcuts are ignored when focus is in an input field.

## Commands

- **Run**: Open `pomodoro.html` in any browser (no build step or server required)
- **No lint/tests**: This project has no test runner, linter, or build tooling
