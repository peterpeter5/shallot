from hypothesis import HealthCheck, settings

settings.register_profile(
    "shallot_profile", suppress_health_check=[HealthCheck.function_scoped_fixture]
)
settings.load_profile("shallot_profile")