EXIT_OK = 0
EXIT_INPUT = 2
EXIT_REFUSED = 3
EXIT_PROVIDER = 4


class AdapterError(Exception):
    exit_code = EXIT_INPUT


class InputError(AdapterError):
    """The request, the environment, or an input file is wrong."""

    exit_code = EXIT_INPUT


class Refused(AdapterError):
    """A spending or people gate said no."""

    exit_code = EXIT_REFUSED


class ProviderError(AdapterError):
    """The provider failed, timed out, or moderated the job."""

    exit_code = EXIT_PROVIDER
