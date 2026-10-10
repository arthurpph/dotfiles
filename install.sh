#!/bin/sh
set -eu
export LC_ALL=C

REPO_URL="https://github.com/arthurpph/config.git"
DOTFILES="$HOME/.dotfiles"
DESKTOP=""
MODE="--install"
for argument in "$@"; do
    case "$argument" in
        hyprland|sway|kde|cosmic|none) DESKTOP="$argument" ;;
        --install|--apply|--dry-run|--packages) MODE="$argument" ;;
        -h|--help)
            echo 'Usage: install.sh [hyprland|sway|kde|cosmic|none] [--install|--apply|--dry-run|--packages]'
            echo 'No desktop argument: choose interactively. Shared application configs are always included.'
            echo '--install: install packages and configure everything (default).'
            echo '--apply: configure without installing packages. --dry-run: preview only.'
            exit 0 ;;
        *) echo "Unknown argument: $argument" >&2; exit 2 ;;
    esac
done
if [ -z "$DESKTOP" ]; then
    echo 'Choose a desktop: hyprland, sway, kde, cosmic, or none (applications only).'
    printf 'Desktop: '
    if ! IFS= read -r DESKTOP; then
        echo 'Specify a desktop argument when running without interactive input.' >&2
        exit 2
    fi
    case "$DESKTOP" in
        hyprland|sway|kde|cosmic|none) ;;
        *) echo "Unknown desktop: $DESKTOP" >&2; exit 2 ;;
    esac
fi
if [ "$(id -u)" = 0 ] && [ "$MODE" != --dry-run ]; then
    echo 'Run this script as your regular user; it invokes sudo when needed.' >&2
    exit 1
fi

# Works both as a checked-out file and through sh -c "$(curl ...)".
SCRIPT_DIRECTORY=""
if [ -f "$0" ]; then
    SCRIPT_DIRECTORY=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fi
if [ -n "$SCRIPT_DIRECTORY" ] && [ -f "$SCRIPT_DIRECTORY/scripts/install.sh" ]; then
    DOTFILES="$SCRIPT_DIRECTORY"
else
    if [ "$MODE" = --dry-run ] && [ ! -f "$DOTFILES/scripts/install.sh" ]; then
        echo "Would clone $REPO_URL into $DOTFILES, then configure $DESKTOP and shared applications."
        exit 0
    fi
    if ! command -v git >/dev/null 2>&1; then
        if [ "$MODE" != --install ] && [ "$MODE" != --packages ]; then
            echo 'Git is required to download the dotfiles.' >&2
            exit 1
        fi
        sudo pacman -Syu --needed git
    fi
    if [ ! -e "$DOTFILES" ]; then
        git clone --recurse-submodules "$REPO_URL" "$DOTFILES"
    elif [ -d "$DOTFILES/.git" ]; then
        if [ "$MODE" != --dry-run ]; then
            git -C "$DOTFILES" pull --ff-only
        fi
    else
        echo "$DOTFILES already exists and is not a Git checkout." >&2
        exit 1
    fi
fi
exec bash "$DOTFILES/scripts/install.sh" "$DOTFILES" "$DESKTOP" "$MODE"
