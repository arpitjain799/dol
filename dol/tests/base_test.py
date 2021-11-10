"""Testing base.py objects"""

import pytest
from dol import (
    MappingViewMixin,
    BaseKeysView,
    BaseValuesView,
    BaseItemsView,
    Store,
    wrap_kvs,
    filt_iter,
    cached_keys,
)
from dol.trans import take_everything


class WrappedDict(MappingViewMixin, dict):
    keys_iterated = False

    # you can log method calls
    class KeysView(BaseKeysView):
        def __iter__(self):
            self._mapping.keys_iterated = True
            return super().__iter__()

    # You can add functionality:
    class ValuesView(BaseValuesView):
        def distinct(self):
            return set(self._mapping.values())

    # you can modify existing functionality:
    class ItemsView(BaseItemsView):
        """Just like BaseKeysView, but yields the [key,val] pairs as lists instead of tuples"""

        def __iter__(self):
            return map(list, super().__iter__())


@pytest.mark.parametrize(
    'source_dict, key_input_mapper, key_output_mapper, value_input_mapper, value_output_mapper, postget, key_filter',
    [
        ({'a': 1, 'b': 2, 'c': 3}, None, None, None, None, None, None),
        (
            {'a': 3, 'b': 1, 'c': 3},  # source_dict
            lambda k: k.lower(),  # key_input_mapper
            lambda k: k.upper(),  # key_output_mapper
            lambda v: v // 10,  # value_input_mapper
            lambda v: v * 10,  # value_output_mapper
            lambda k, v: f'{k}{v}',  # postget
            lambda k: k in {'a', 'c'},  # key_filter
        ),
    ],
)
def test_mapping_views(
    source_dict,
    key_input_mapper,
    key_output_mapper,
    value_input_mapper,
    value_output_mapper,
    postget,
    key_filter,
):
    def assert_store_functionality(
        store,
        key_output_mapper=None,
        value_output_mapper=None,
        postget=None,
        key_filter=None,
    ):
        key_output_mapper = key_output_mapper or (lambda k: k)
        value_output_mapper = value_output_mapper or (lambda v: v)
        postget = postget or (lambda k, v: v)
        key_filter = key_filter or (lambda k: True)
        assert list(store) == [
            key_output_mapper(k) for k in source_dict if key_filter(k)
        ]
        assert not store.keys_iterated
        assert list(store.keys()) == [
            key_output_mapper(k) for k in source_dict.keys() if key_filter(k)
        ]
        assert store.keys_iterated
        assert list(store.values()) == [
            postget(key_output_mapper(k), value_output_mapper(v))
            for k, v in source_dict.items()
            if key_filter(k)
        ]
        assert sorted(store.values().distinct()) == sorted(
            {
                postget(key_output_mapper(k), value_output_mapper(v))
                for k, v in source_dict.items()
                if key_filter(k)
            }
        )
        assert list(store.items()) == [
            [
                key_output_mapper(k),
                postget(key_output_mapper(k), value_output_mapper(v)),
            ]
            for k, v in source_dict.items()
            if key_filter(k)
        ]

    wd = WrappedDict(**source_dict)
    assert_store_functionality(wd)

    wwd = Store.wrap(WrappedDict(**source_dict))
    assert_store_functionality(wwd)

    WWD = Store.wrap(WrappedDict)
    wwd = WWD(**source_dict)
    assert_store_functionality(wwd)

    wwd = wrap_kvs(
        WrappedDict(**source_dict),
        id_of_key=key_input_mapper,
        key_of_id=key_output_mapper,
        data_of_obj=value_input_mapper,
        obj_of_data=value_output_mapper,
        postget=postget,
    )
    assert_store_functionality(
        wwd,
        key_output_mapper=key_output_mapper,
        value_output_mapper=value_output_mapper,
        postget=postget,
    )

    wwd = filt_iter(WrappedDict(**source_dict), filt=key_filter or take_everything)
    assert_store_functionality(wwd, key_filter=key_filter)