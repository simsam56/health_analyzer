#!/bin/bash
# Ancien lanceur PerformOS — redirige vers Board
# Utilisez Lancer_Board.command ou Board.app à la place

echo "PerformOS a été renommé Board."
echo "Redirection vers Board..."
echo ""

cd "$(dirname "$0")" || exit 1
exec bash board.sh
