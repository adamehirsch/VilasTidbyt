#!/usr/bin/env python

import argparse
import logging

import arrow
from PIL import ImageDraw, ImageFont

import utils

FBCAL = utils.TIDBYT_CREDS["freeBusyCal"]
FBCOLOR = utils.TIDBYT_CREDS["freeBusyColor"]
FBINSTALL = utils.TIDBYT_CREDS["freeBusyInstallation"]

# Meant to read events from one calendar and draw them as solid blocks of
# color on a 7-day x 24 hour calendar on the bottom 24 pixels of the display

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)


def draw_week_events(img, events, image_name):
    d = ImageDraw.Draw(img)
    teenyfont = ImageFont.load("fonts/4x6.pil")

    tf = arrow.now(utils.LOCALTZ).floor("day")

    for i, e in enumerate(events):
        shift_start, shift_end, shift_duration = utils.get_event_times(e, tf)
        days_forward = shift_start.days

        # position the busy-blocks
        x_start = days_forward * 9 + 1
        x_end = x_start + 7

        hour_start = shift_start.seconds // 3600
        hour_end = shift_end.seconds // 3600
        y_start = 8 + hour_start
        y_end = 8 + hour_end

        if shift_start.days == shift_end.days:
            # this is a same-day shift; one rectangle
            d.rectangle([x_start, y_start, x_end, y_end], fill=FBCOLOR)
        else:
            # draw a rectangle to finish the day
            d.rectangle([x_start, y_start, x_end, 32], fill=FBCOLOR)
            # and another at the top of the next day, unless it's the last day
            if shift_end.days < 7:
                d.rectangle([x_start + 9, 8, x_end + 9, y_end], fill=FBCOLOR)

        # this is meant to put the length of the shift above the block.
        # Don't insert it if the column starts too high (for a weirdly early shift start)
        if y_start > 14:
            text_x = x_start + (2 if (shift_duration.seconds // 3600) < 10 else 0)
            text_y = y_start - 6

            hours_length = shift_duration.seconds // 3600

            # is there another event immediately after this one?
            if len(events) > i + 1:
                next_event = events[i + 1]
                next_start, next_end, next_duration = utils.get_event_times(
                    next_event, tf
                )
                if shift_end == next_start:
                    # the next shift starts immediately after the current one; sigh
                    hours_length += next_duration.seconds // 3600

            # Only draw the hours-length if the pixel isn't already drawn on
            if img.getpixel((text_x, text_y)) != (0, 0, 0, 0):
                logging.debug("skipping drawing hours on populated pixel")
                continue

            d.text(
                xy=(
                    # center single digits over the column
                    text_x,
                    text_y,
                ),
                text=str(hours_length),
                font=teenyfont,
                fill="#fff",
            )
    img.save(image_name)


def main():
    fb_events = utils.fetch_events(
        FBCAL,
        arrow.now(utils.LOCALTZ).floor("day"),
        arrow.now(utils.LOCALTZ).shift(days=6).ceil("day"),
    )
    if fb_events:
        image_name = utils.TIDBYT_CREDS.get("freeBusyImage", "working.gif")
        logging.debug("posting events to Tidbyt")
        week_image = utils.draw_week_ahead()
        draw_week_events(
            week_image,
            fb_events,
            image_name,
        )
        utils.post_image(image_name, FBINSTALL)
    else:
        logging.debug("no events to post")
        utils.remove_installation(FBINSTALL)


if __name__ == "__main__":
    main()
