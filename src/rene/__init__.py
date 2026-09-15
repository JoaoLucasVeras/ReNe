"""ReNe research package."""

from rene.envs.registration import register_environments

register_environments()

__all__ = ["register_environments"]
