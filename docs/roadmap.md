# Roadmap

## Shipped in 0.1

- Stardust, Switcheroo and Blink, any combination at once, gesture per effect, no clashes
- Room capture, built-in backdrops, custom images
- Edge-aware matting tuned to keep chairs out of the cutout
- OBS Virtual Camera output, guided meeting setup with one-click OBS install
- Start-up checks for system, models, camera permission and the meeting driver

## Shipped in 0.2

- Cloak (open palm): invisibility with a refracting ripple
- Modes that keep you in view: Clones (crossed fingers), Spotlight (finger up)
- Reactions that play once and need no background: Confetti (thumbs up), Hearts (heart hands), Rain cloud (thumbs down)

## Next: more gesture effects

| Gesture | Effect |
|---|---|
| Rock horns | Lightning storm backdrop |
| Finger frame | Polaroid snapshot drops into the corner |
| Index finger up | Spotlight; the room dims |
| Finger to lips | Silent-film mode: sepia, grain, title card |
| Raised hand | Raise-hand badge for meetings |

## Later: voice spells and face masks

Say a phrase, such as "I am the night", and a mask appears on your face and follows you as you move and turn.

- **Voice trigger**: offline keyword spotting with [Vosk](https://alphacephei.com/vosk/) (Apache 2.0, about 40 MB English model) restricted to the configured phrases. Nothing is sent to the cloud. Needs microphone permission.
- **Tracking**: the face landmarker already gives 478 points and a head-pose matrix. Masks are warped onto the face mesh triangle by triangle, so they stay attached through movement, turning and talking, with smoothing to stop jitter.
- **Masks**: original masks shipped with Hocus (for example a bat-eared night cowl), plus importing your own PNG masks. Masks of trademarked characters are not shipped.
