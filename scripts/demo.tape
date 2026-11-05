# Record a clean demo GIF with VHS (https://github.com/charmbracelet/vhs):
#   brew install vhs
#   vhs scripts/demo.tape        # writes assets/demo.gif
#
# This records the OFFLINE demo (runs anywhere). To capture the REAL live Switch
# run instead, set up .env per docs/live-switch.md and replace the `redroom demo`
# line below with:   redroom run
Output assets/demo.gif
Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 680
Set Padding 18
Set Theme "Dracula"
Hide
Type "source .venv/bin/activate" Enter
Show
Type "redroom demo --offline --auto-approve" Sleep 500ms Enter
Sleep 35s
