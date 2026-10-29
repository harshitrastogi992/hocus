# Adding an effect

1. Create `engine/src/hocus/effects/<name>.py` with a subclass of `Effect`:

   ```python
   class Confetti(Effect):
       id = "confetti"
       name = "Confetti"
       description = "Party poppers burst behind you."
       default_gesture = "thumbs_up"
       out_seconds = 1.2
       in_seconds = 0.6

       def render(self, scene, direction, t):
           ...  # return a BGR uint8 frame

       def render_hidden(self, scene, t):
           ...  # optional; defaults to the background
   ```

   `scene.frame` is the live camera frame, `scene.background` what shows when you are gone, and `scene.mask` the person matte in [0, 1]. Use `begin()` for anything worked out once per transition, such as particle positions.

2. Register it in `effects/__init__.py` (`EFFECT_TYPES`).
3. If it needs a new gesture, add a shape test to `gestures/shapes.py` and a `GestureSpec` to `gestures/catalog.py`, and give `catalog.detect` a priority for it.
4. Add an icon in `app/src/components/EffectsPanel.tsx` (`ICONS`) and a sound in `app/src/lib/sounds.ts`.
5. Default gestures must not clash: `tests/test_settings.py` checks this.
6. Render it with `scripts/preview_effects.py` and keep it under about 15 ms per 720p frame.

Effects are not limited to vanishing. Set `kind = "toggle"` and an `active_label` for a mode that keeps you in view: `render_hidden` then draws the live person plus the mode (see `clones.py` and `spotlight.py`).

## Adding a reaction

A reaction plays once over whatever is on screen and needs no background. Subclass `Reaction` in `engine/src/hocus/reactions/`, set `seconds`, and implement `render(output, mask, person_visible, t)`. Use `self.behind(output, layer, mask, person_visible)` to keep the person in front of what you draw. `begin(shape, observation)` receives the hand and face landmarks from the trigger, for example to start hearts at the hands. Register it in `reactions/__init__.py` (`REACTION_TYPES`).
