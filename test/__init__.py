def awaitable_mock(func):
    async def awaitable(*args, **kwargs):
        return func(*args, **kwargs)
    return awaitable