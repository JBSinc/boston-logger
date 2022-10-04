from copy import deepcopy

MASK_STRING = "*** masked ***"

_global_masks = set()
_mask_processors = {}


def chain_mask(data):
    """Return data with all values masked."""
    if data is None:
        return None

    if isinstance(data, dict):
        from .config import config

        if config.SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS:
            return {k: MASK_STRING for k in data.keys()}
        else:
            return {MASK_STRING: MASK_STRING}
    elif isinstance(data, list):
        return [chain_mask(x) for x in data]
    else:
        return MASK_STRING


class SensitivePaths:
    def __init__(self, *args: str):
        # str -> Union(dict, bool)
        # Nested dictionaries represent paths
        # A "True" value means the data should be masked from that path and
        # all children.
        self.root_paths = {}

        # '*' matches any key at ONE level.
        # Leading and trailing '/' has no effect
        #
        # args = [ 'obj/key1', '/obj/key2', 'obj/key2/ignored', 'obj/*/nested1/' ]
        # Produces root_paths of:
        #   {
        #       'obj': {
        #           'key1': True,
        #           'key2': True,
        #           '*': {
        #               'nested1': True,
        #           }
        #       }
        #   }

        for path in args:
            current_dict = self.root_paths
            # Leading and trailing '/' has no effect
            keys = path.strip("/").split("/")
            while keys:
                k = keys.pop(0)
                if len(keys) == 1 and keys[0] == "*":
                    # Terminal "*" is the same as not having it
                    # Everything from the current path down is sanitized
                    current_dict[k] = True
                    break
                if len(keys) == 0:
                    current_dict[k] = True
                else:
                    current_dict.setdefault(k, {})
                    current_dict = current_dict[k]
                    if current_dict is True:
                        # We hit a previous path, underwhich everything should
                        # be masked. Skip the rest of this path, it will all be
                        # masked
                        break

    def process(self, data: dict):
        """Mutates data to apply sanitation.

        Sanitation only happens if config.ENABLE_SENSITIVE_PATHS_PROCESSOR is True.
        """
        from .config import config

        if config.ENABLE_SENSITIVE_PATHS_PROCESSOR:
            SensitivePaths._sanitize_dict(self.root_paths, data)

    @staticmethod
    def _sanitize_dict(paths, data: dict):
        """Mutates data to sanitize values in matching paths."""

        if "*" in paths:
            nested_paths = paths["*"]
            if nested_paths is True:
                from .config import config

                if config.SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS:
                    # Special case for single '*' entry
                    data.update(chain_mask(data))
                else:
                    data.clear()
                    data[MASK_STRING] = MASK_STRING
            else:
                # Normally check all values for the paths under the '*'
                for v in data.values():
                    SensitivePaths._sanitize_any(nested_paths, v)

        for k, v in data.items():
            nested_paths = paths.get(k)
            if nested_paths is None:
                # k not in paths -> don't sanitize
                pass
            elif nested_paths is True:
                # Mask below this path
                data[k] = chain_mask(v)
            else:
                # Process nested_paths
                SensitivePaths._sanitize_any(nested_paths, data[k])

    @staticmethod
    def _sanitize_any(paths, data):
        """Mutates data to sanitize values in matching paths."""

        if isinstance(data, dict):
            SensitivePaths._sanitize_dict(paths, data)

        elif isinstance(data, (list, tuple)):
            # If there are Lists of objects process each object.
            # The list does not add a path element
            # SensitivePaths( 'obj1/key1' )
            # WOULD mask the key1's in the folowing object:
            #   {
            #       'obj1': [
            #           {
            #               'key1': 'sensitive',
            #           }, {
            #               'key1': 'sensitive',
            #           },
            #       ]
            #   }

            for item in data:
                SensitivePaths._sanitize_any(paths, item)
        # else:
        # Data isn't itterable, and path didn't match, nothing to do


def add_mask_processor(mask_name, processor, *, is_global=False):
    """Register processor as mask_name

    processor must have a method process(data, is_query_string) which mutates
    data to apply sanitation.

    if is_global == True, this processor will apply to all data sanitation
    """
    _mask_processors[mask_name] = processor
    if is_global:
        _global_masks.add(mask_name)


def remove_mask_processor(mask_name):
    """Unregister a processor, and remove from global list if possible."""
    _mask_processors.pop(mask_name, None)
    try:
        # Remove from global if it exists
        _global_masks.remove(mask_name)
    except KeyError:
        pass


# All is a special name to match all data
add_mask_processor("ALL", SensitivePaths("*"))


def sanitize_data(data: dict, *mask_names):
    """Return copy of data that has been sanitized.

    Global masks, the current SensitivePathContext and any positional args will
    be applied.
    """
    # Avoid circular import
    from .context_managers import SensitivePathContext

    context_mask_names = SensitivePathContext.get_mask_names()
    mask_names = set(mask_names) | context_mask_names | _global_masks

    masked_data = deepcopy(data)

    for mask_name in mask_names:
        _mask_processors[mask_name].process(masked_data)

    return masked_data
