---
layout: post
title: "Progress report"
tagline: "Repetier support, logging and more"
description: ""
category: 
tags: []
---
{% include JB/setup %}

Weekly update regarding development progress:

* The most labor intensive change this week(end) is that OctoPrint now -- after intense debugging across the pond with
  [Tom Perry](https://github.com/daftscience) -- supports the Repetier firmware. In order for this to work I had to overhaul major parts of the communication
  layer inherited from Cura, including the resend mechanism, but it finally resulted in a success. The outcome of
  this -- among some new gray hairs -- were two new configuration settings,
  "Send a checksum with every command" and "Send M110 commands with target line number as N-prefix" in the feature tab,
  that you'll have to tick in order to be able to print on a Repetier enabled printer.
  For now the code will only be available in the ["repetier" branch](https://github.com/foosel/OctoPrint/tree/repetier)
  as I want to test the overhauled communcation a bit more with Marlin (you are btw welcome to help here!) before I
  merge it into devel and after that into master, but it's looking promising.
* As yesterday's mini update suggested, I also added a new logfile `terminal.log` which logs the serial communication
  that so far only available in the terminal tab. Due to performance reasons you'll have to supply the `--debug` command
  switch on OctoPrint's startup to enable this.
* [Dale Price](https://github.com/daprice) sent a pull request fixing an iOS Bug that caused control buttons only working
  once (due to iOS caching the POST request... I don't even...)
* The Raspberry Pi setup guide and configuration documentation got moved to the [wiki](https://github.com/foosel/OctoPrint/wiki)
* I also fixed a couple of small things along the way (that I'm completely unable to recall right now)

No screenshots today, since all of this stuff was only in the backend. Maybe Tom Perry will give me permission to post
a shot of his very special whiteboard though, to make up for it ;)