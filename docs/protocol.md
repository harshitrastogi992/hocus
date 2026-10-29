# Engine protocol

WebSocket on `ws://127.0.0.1:<port>/?token=<token>`. The engine prints `HOCUS_READY <port>` on stdout once it is listening. Connections with a wrong token are closed with code 4401.

Text frames carry JSON. Binary frames are JPEG preview images (960 px wide). A slow client receives only the newest frame.

## Engine to UI

| `type` | When | Fields |
|---|---|---|
| `state` | On connect and after every settings change | `settings`, `catalog` (effects with `kind` of `vanish`, `toggle` or `reaction` and an `active_label`; gestures; presets with thumbnails; resolutions), `status` |
| `checks` | On connect, after `run_checks` and after an OBS install | `items[]` (`id`, `label`, `state`: ok/warn/fail, `detail`, `required`, `action_label`, `action_url`), `camera_settings_url`, `can_install_obs`, `platform` |
| `status` | About 8 times a second | `stage`, `phase`, `effect`, `reactions` (ids playing now), `hold` (`gesture`, `progress`), `plate`, `plate_countdown`, `background_ready`, `camera`, `virtual_camera`, `fps` |
| `effect` | A transition or reaction starts | `effect`, `direction` (`out` or `in`; always `out` for a reaction). The UI plays the sound. |
| `notice` | Something to tell the user | `level` (`info` or `error`), `message` |
| `install` | OBS install progress | `state` (`running`, `done`, `failed`), `message` |

## UI to engine

| `type` | Fields | Effect |
|---|---|---|
| `update_settings` | `patch` (deep-merged) | Validated, saved and applied. On error the engine sends a `notice` and the unchanged `state`. |
| `capture_plate` | | Three-second countdown, then captures the empty room |
| `toggle` | `effect` (optional) | Vanish or switch a mode on with that effect (or the first enabled vanishing effect), or return if hidden. A reaction id plays that reaction once. |
| `run_checks` | | Re-run start-up checks |
| `install_obs` | | Install OBS Studio with Homebrew (macOS) or winget (Windows) |
| `open_obs` | | Launch OBS so the user can activate its virtual camera |
| `get_state` | | Resend `state` |
