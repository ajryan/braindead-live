#!/usr/bin/env bash
# Encode the landing-page background video from the multicam master.
#
# The master is NOT in the repo (391 MB). Pass its path as $1, or set HERO_SRC.
#
# Everything that defines the look lives here on purpose: an earlier version
# of this clip was graded with ffmpeg values that were never written down, so
# they had to be reverse-engineered from the encoded file.
#
# Landscape and portrait are the same window, cropped differently. They stay
# separate files so each is framed for the shape it fills, and so the crop
# can change later without re-cutting both.

set -euo pipefail

SRC="${1:-${HERO_SRC:-$HOME/Downloads/Foreign Feeling MULTICAM [ patreon ]_1080p.mp4}}"
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/src/assets/video"

# ---- source map ----------------------------------------------------------
# The master alternates full-frame single-camera shots (0-236s) with
# composited multi-up grids (2-up from ~240s, 2x2 later). Only the full-frame
# region is usable. Within it the edit cuts roughly every 8s; cut list from
# ffmpeg scene detection at threshold 0.08 (0.20 misses real cuts).

# ---- landscape: the keyboard shot ----------------------------------------
# 203.57-213.98 is the only >=10s cut-free shot where the keyboard player is
# large and unmistakable. They sit left of centre, which suits the layout:
# the flyer occupies mid-frame, so an off-centre subject reads around it.
# Margin is thin - keep clear of both cuts.
LAND_START=204
LAND_DUR=9.8

# ---- portrait: the same window --------------------------------------------
# Same shot as landscape, cropped for the shape. x=540, not the geometric
# centre: centring (x=656) reproduces what a portrait viewport shows of the
# landscape file, but that lands on bare keyboard with the player reduced to
# a sleeve at the frame edge. Shifting left puts both hands on the keys in
# the lower band - the part that still reads once the flyer sits high - with
# the player's jacket anchoring the left. x=440 is the alternative: more of
# the player's body, but the hands ride up behind the CTA.
PORT_START=$LAND_START
PORT_DUR=$LAND_DUR
PORT_CROP="crop=608:1080:540:0"

# ---- grade ---------------------------------------------------------------
# Lifted black point, reduced contrast and saturation, so the overlaid flyer
# and CTA stay readable. The line through shadows and midtones is the one
# measured off the previous clip, which kept the site's established look:
# luma mapped 0->24, 128->142, 224->232, i.e. out = 0.891*in + 0.0715.
#
# The top end departs from that line on purpose. Stage key lights blow out
# the player's pale jacket and the white keys, which popped hard enough to
# pull attention off the flyer. The curve tracks the original through 0.4
# and then rolls off, landing full white at 0.80 instead of 0.96. Shadows
# and midtones are deliberately untouched so only the glare changes.
GRADE="eq=saturation=0.926,curves=all='0/0.072 0.2/0.250 0.4/0.428 0.6/0.590 0.8/0.700 1/0.800'"

# Light denoise. Stage footage is noisy and strobing lights defeat
# inter-frame prediction; verified at 1:1 this is indistinguishable from no
# denoise while costing less bitrate. Stronger settings go waxy.
DENOISE="hqdn3d=3:2:5:4"

FPS=24   # it's a background loop, not a performance video

enc() { # name  start  dur  filters  crf
  ffmpeg -v error -ss "$2" -t "$3" -i "$SRC" -an \
    -vf "$GRADE,$DENOISE,$4" -r "$FPS" \
    -c:v libx264 -crf "$5" -preset slow -pix_fmt yuv420p -movflags +faststart \
    "$OUT/$1" -y
  printf '  %-24s %6.2f MB\n' "$1" "$(echo "scale=2; $(stat -f%z "$OUT/$1")/1048576" | bc)"
}

poster() { # name  start  filters
  ffmpeg -v error -ss "$2" -i "$SRC" -frames:v 1 -vf "$GRADE,$DENOISE,$3" -q:v 5 "$OUT/$1" -y
  printf '  %-24s %6.1f KB\n' "$1" "$(echo "scale=1; $(stat -f%z "$OUT/$1")/1024" | bc)"
}

echo "source: $SRC"
echo "window: ${LAND_START}s +${LAND_DUR}s (landscape and portrait)"
echo "video:"
enc hero-1080.mp4     "$LAND_START" "$LAND_DUR" "scale=1920:1080" 31
enc hero-720.mp4      "$LAND_START" "$LAND_DUR" "scale=1280:720"  27
enc hero-portrait.mp4 "$PORT_START" "$PORT_DUR" "$PORT_CROP"      27
echo "posters:"
poster hero-poster.jpg          "$LAND_START" "scale=1280:720"
poster hero-poster-portrait.jpg "$PORT_START" "$PORT_CROP,scale=608:1080"
