import copy

import pytest

from boston_logger.sensitive_paths import (
    MASK_STRING,
    SensitivePaths,
    _global_masks,
    _mask_processors,
    add_mask_processor,
    chain_mask,
    remove_mask_processor,
    sanitize_data,
)


def test_chain_mask_handles_none():
    # Mostly for coverage
    assert chain_mask(None) is None


def test_remove_safe():
    # GIVEN processor that does not exist
    assert "N/A" not in _mask_processors
    assert "N/A" not in _global_masks
    # WHEN removed
    remove_mask_processor("N/A")
    # THEN there is no error


@pytest.mark.parametrize(
    "paths, expected_root_paths",
    [
        (
            # Leading and Trailing /'s removed
            # Resulting duplicates, collapsed
            ["/obj1/key1", "obj1/key1", "obj1/key2/"],
            {
                "obj1": {
                    "key1": True,
                    "key2": True,
                },
            },
        ),
        (
            # Midpath *'s honored
            # Terminal *'s removed
            ["/obj1/*/key1", "obj1/key2/*"],
            {
                "obj1": {
                    "*": {
                        "key1": True,
                    },
                    "key2": True,
                },
            },
        ),
        (
            # Depth first collapsed
            ["obj1/nested/key1", "obj1/nested"],
            {
                "obj1": {
                    "nested": True,
                },
            },
        ),
        (
            # Deeper Depth first collapsed
            ["obj1/nested/key1/deeper", "obj1/nested/key1", "obj1/nested"],
            {
                "obj1": {
                    "nested": True,
                },
            },
        ),
        (
            # Depth second collapsed
            ["obj1/nested", "obj1/nested/key1"],
            {
                "obj1": {
                    "nested": True,
                },
            },
        ),
        (
            # Deeper Depth second collapsed
            ["obj1/nested", "obj1/nested/key1", "obj1/nested/key1/deeper"],
            {
                "obj1": {
                    "nested": True,
                },
            },
        ),
    ],
)
def test_root_paths(paths, expected_root_paths):
    """
    GIVEN a set of paths
    THEN an expected root_paths dict will be created
    """

    sp = SensitivePaths(*paths)

    assert sp.root_paths == expected_root_paths


class TestPaths:
    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        mocker.patch(
            "boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True
        )
        self.sp = SensitivePaths(
            "obj1/key1", "obj1/key2", "obj2/*/wild", "obj2/nested/calm"
        )

    @pytest.mark.parametrize(
        "data, expected_masked_data",
        [
            (
                # Simple match
                # Extra data passed
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": "secret",
                        "key2": "hidden",
                        "key3": "shown",
                    },
                },
                {
                    "obj1": {
                        "key1": MASK_STRING,
                        "key2": MASK_STRING,
                        "key3": "shown",
                    },
                    "obj2": "shown",
                },
            ),
            (
                # list value
                {"obj1": {"key1": ["x", "y", "z"]}},
                {"obj1": {"key1": [MASK_STRING] * 3}},
            ),
            (
                # lists of objects check each object
                {
                    "obj1": [
                        {
                            "key1": "secret",
                            "key2": "hidden",
                            "key3": "shown",
                        },
                        {
                            "key1": "secret",
                            "key2": "hidden",
                            "key3": "shown",
                        },
                    ],
                },
                {
                    "obj1": [
                        {
                            "key1": MASK_STRING,
                            "key2": MASK_STRING,
                            "key3": "shown",
                        },
                        {
                            "key1": MASK_STRING,
                            "key2": MASK_STRING,
                            "key3": "shown",
                        },
                    ],
                },
            ),
            (
                # deeper lists ignored
                # Extra data passed
                {
                    "obj2": "shown",
                    "obj1": [
                        {
                            "key1": "secret",
                            "key2": "hidden",
                            "key3": "shown",
                        },
                        [
                            {
                                "key1": "secret",
                                "key2": "hidden",
                                "key3": "shown",
                            },
                        ],
                    ],
                },
                {
                    "obj1": [
                        {
                            "key1": MASK_STRING,
                            "key2": MASK_STRING,
                            "key3": "shown",
                        },
                        [
                            {
                                "key1": MASK_STRING,
                                "key2": MASK_STRING,
                                "key3": "shown",
                            },
                        ],
                    ],
                    "obj2": "shown",
                },
            ),
            (
                # Mask past one star
                # But not two level
                {
                    "obj2": {
                        "key1": {
                            "wild": "hidden",
                        },
                        "key2": {
                            "wild": "hidden",
                        },
                        "key3": {
                            "nested": {
                                "wild": "shown",
                            },
                        },
                    },
                },
                {
                    "obj2": {
                        "key1": {
                            "wild": MASK_STRING,
                        },
                        "key2": {
                            "wild": MASK_STRING,
                        },
                        "key3": {
                            "nested": {
                                "wild": "shown",
                            },
                        },
                    },
                },
            ),
            (
                # Lists and stars
                {
                    "obj2": [
                        {
                            "key1": {
                                "wild": "hidden",
                            },
                        },
                        {
                            "key2": {
                                "wild": "hidden",
                            },
                        },
                        {
                            "key3": {
                                "nested": {
                                    "wild": "shown",
                                },
                            },
                        },
                    ]
                },
                {
                    "obj2": [
                        {
                            "key1": {
                                "wild": MASK_STRING,
                            },
                        },
                        {
                            "key2": {
                                "wild": MASK_STRING,
                            },
                        },
                        {
                            "key3": {
                                "nested": {
                                    "wild": "shown",
                                },
                            },
                        },
                    ],
                },
            ),
            (
                # Star and others
                {
                    "obj2": {
                        "key1": {
                            "wild": "hidden",
                        },
                        "nested": {
                            "calm": "hidden",
                        },
                    }
                },
                {
                    "obj2": {
                        "key1": {
                            "wild": MASK_STRING,
                        },
                        "nested": {
                            "calm": MASK_STRING,
                        },
                    }
                },
            ),
        ],
    )
    def test_data(self, data, expected_masked_data):
        # There is no return data
        assert self.sp.process(data) is None
        # Data has been changed in place
        assert data == expected_masked_data


class TestAll:
    @pytest.fixture(autouse=True, scope="class")
    def setup(self, class_mocker):
        class_mocker.patch(
            "boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True
        )

    @pytest.mark.parametrize(
        "data, expected_hide_nested, expected_show_nested",
        [
            (
                # dict masked
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": "secret",
                        "key2": "hidden",
                        "key3": "shown",
                    },
                },
                {
                    MASK_STRING: MASK_STRING,
                },
                {
                    "obj2": MASK_STRING,
                    "obj1": MASK_STRING,
                },
            ),
            (
                # dict with list masked
                {
                    "obj2": "shown",
                    "list1": [
                        "secret",
                        "hidden",
                        "shown",
                    ],
                },
                {
                    MASK_STRING: MASK_STRING,
                },
                {
                    "obj2": MASK_STRING,
                    "list1": MASK_STRING,
                },
            ),
        ],
    )
    def test_data(self, mocker, data, expected_hide_nested, expected_show_nested):
        orig_data = copy.deepcopy(data)
        # Returned data is sanitized
        # ALL is a built-in filter, but not globally active
        assert sanitize_data(data, "ALL") == expected_hide_nested
        # Data has not been altered
        assert data == orig_data

        mocker.patch(
            "boston_logger.config.config.SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS", True
        )
        assert sanitize_data(data, "ALL") == expected_show_nested


class TestGlobal:
    @pytest.fixture(autouse=True, scope="class")
    def setup(self, class_mocker):
        class_mocker.patch(
            "boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True
        )
        add_mask_processor(
            "Simple", SensitivePaths("obj1/key1", "list1"), is_global=True
        )
        yield
        remove_mask_processor("Simple")

    @pytest.mark.parametrize(
        "data, expected_hide_nested, expected_show_nested",
        [
            (
                # dict masked
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": "secret",
                        "key3": "shown",
                    },
                },
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": MASK_STRING,
                        "key3": "shown",
                    },
                },
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": MASK_STRING,
                        "key3": "shown",
                    },
                },
            ),
            (
                # nested dict masked
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": {"maybe_show": "secret"},
                        "key3": "shown",
                    },
                },
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": {MASK_STRING: MASK_STRING},
                        "key3": "shown",
                    },
                },
                {
                    "obj2": "shown",
                    "obj1": {
                        "key1": {"maybe_show": MASK_STRING},
                        "key3": "shown",
                    },
                },
            ),
            (
                # dict with list masked
                {
                    "obj2": "shown",
                    "list1": [
                        "secret",
                        "hidden",
                        "shown",
                    ],
                },
                {
                    "obj2": "shown",
                    "list1": [MASK_STRING] * 3,
                },
                {
                    "obj2": "shown",
                    "list1": [MASK_STRING] * 3,
                },
            ),
        ],
    )
    def test_data(self, mocker, data, expected_hide_nested, expected_show_nested):
        orig_data = copy.deepcopy(data)
        # Returned data is sanitized by global processor(s)
        assert sanitize_data(data) == expected_hide_nested
        # Data has not been altered
        assert data == orig_data

        # When Show key is enabled, more data is visible
        mocker.patch(
            "boston_logger.config.config.SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS", True
        )
        assert sanitize_data(data) == expected_show_nested
