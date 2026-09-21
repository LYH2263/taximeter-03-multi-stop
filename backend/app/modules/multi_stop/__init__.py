"""Multi-stop module: one fare over ordered legs, persistable via calc_runs.

Layering: engine (pure) <- service (persistence) <- router (HTTP). The
package __init__ only re-exports the engine so the service layer never
pulls in the web layer.
"""

from app.modules.multi_stop.engine import calc_multi_stop

__all__ = ["calc_multi_stop"]
