# LIVE recording of the real Switch run. Prereqs: Switch running, .env filled, agent invited to the
# room (see docs/live-switch.md). Then:  brew install vhs ; vhs scripts/demo-live.tape
#
# Outputs an MP4 (archive) AND a GIF to *-live names so the offline assets/demo.gif is NOT touched.
# Approve in the Mattermost room promptly after the findings appear (within the Sleep window).
Output assets/demo-live.mp4
Output assets/demo-live.gif
Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 680
Set Padding 18
Set Theme "Dracula"
Hide
Type "source .venv/bin/activate" Enter
Show
Type "redroom run" Sleep 500ms Enter
Sleep 75s
