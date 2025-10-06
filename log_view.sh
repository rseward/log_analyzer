#!/bin/bash

# brew install ov
ov -H1 --skip-lines 4 --header 2 --column-delimiter "|" --column-mode --align --column-rainbow --multi-color "error,warn,info,debug,not,^.{24}" --alternate-rows
