"""Adapter contract checks with public API doubles; not FreeCAD integration."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from freecad_cam_libraries.compatibility import FreeCADAdapter
from freecad_cam_libraries.validation import Tool
from test_installer import definition


class Uri(str):
    @property
    def asset_id(self):
        return self.split('://',1)[1]


class NativeLibrary:
    @classmethod
    def from_dict(cls, data, ident, dependencies):
        return SimpleNamespace(data=copy.deepcopy(data),ident=ident,deps=dependencies)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter=object.__new__(FreeCADAdapter)
        self.adapter.assets=Mock()
        self.adapter.AssetUri=Uri
        self.adapter.Library=NativeLibrary
        self.adapter.serializer=Mock()
        self.adapter.Shape=Mock()
        self.adapter.shape_serializer=object()

    def test_native_prepare_resolves_serializer_dependencies(self):
        data=definition();tool=Tool(Path(data['id']+'.fctb'),data,json.dumps(data).encode())
        uri=Uri('toolbitshape://drill')
        self.adapter.serializer.extract_dependencies.return_value=[uri]
        raw=b'native FCStd shape bytes'
        self.adapter.assets.get_raw.return_value=raw
        shape=object();self.adapter.Shape.from_bytes.return_value=shape
        self.adapter.prepare(tool)
        self.adapter.assets.get_raw.assert_called_once_with(uri,store=('local','builtin'))
        self.adapter.Shape.from_bytes.assert_called_once_with(
            raw,'drill',dependencies=None,serializer=self.adapter.shape_serializer)
        self.adapter.serializer.deserialize.assert_called_once_with(tool.raw,tool.id,{uri:shape})
        self.adapter.assets.get.assert_not_called()

    def test_register_exact_bytes_through_native_api(self):
        data=definition();tool=Tool(Path(data['id']+'.fctb'),data,json.dumps(data).encode())
        self.adapter.assets.exists.return_value=False
        self.adapter.register(tool,object())
        self.adapter.assets.add_raw.assert_called_once_with('toolbit',tool.id,tool.raw,store='local')
        self.adapter.assets.get.assert_called_once_with('toolbit://'+tool.id)

    def test_register_refuses_existing_uuid(self):
        data=definition();tool=Tool(Path(data['id']+'.fctb'),data,json.dumps(data).encode())
        self.adapter.assets.exists.return_value=True
        self.adapter.assets.get_raw.return_value=tool.raw
        with self.assertRaises(RuntimeError): self.adapter.register(tool,object())
        self.adapter.assets.add_raw.assert_not_called()

    def test_save_uses_native_library_and_asset_add(self):
        data={'version':1,'label':'Test','tools':[{'nr':42,'path':'my-tool.fctb'}]}
        saved=json.dumps(data).encode()
        self.adapter.library_raw=Mock(side_effect=[None,saved])
        bit=object();self.adapter.assets.get.return_value=bit
        self.assertEqual(self.adapter.save_library('test-id',data,None),saved)
        native=self.adapter.assets.add.call_args.args[0]
        self.assertEqual(native.ident,'test-id')
        self.assertEqual(native.deps,{Uri('toolbit://my-tool'):bit})
        self.assertEqual(native.data,data)
        self.assertEqual(self.adapter.assets.add.call_args.kwargs,{'store':'local'})

    def test_save_rejects_concurrent_change(self):
        self.adapter.library_raw=Mock(return_value=b'changed')
        with self.assertRaises(RuntimeError):self.adapter.save_library('id',{},None)
        self.adapter.assets.add.assert_not_called()

    def test_save_detects_unexpected_native_result(self):
        self.adapter.library_raw=Mock(side_effect=[None,b'{}'])
        with self.assertRaises(RuntimeError):self.adapter.save_library('id',{'version':1,'label':'test','tools':[]},None)

    def test_snapshot_local_tools_shadow_builtin_but_libraries_are_local(self):
        def list_assets(kind,store):
            if kind=='toolbit':return [Uri('toolbit://same')]
            return [Uri('toolbitlibrary://lib')]
        self.adapter.assets.list_assets.side_effect=list_assets
        def raw(uri,store):
            if str(uri).startswith('toolbitlibrary'):return b'{"label":"mine","version":1,"tools":[]}'
            return json.dumps({'origin':store}).encode()
        self.adapter.assets.get_raw.side_effect=raw
        tools,libraries=self.adapter.snapshot()
        self.assertEqual(tools['same'],{'origin':'local'})
        self.assertEqual(libraries[0]['label'],'mine')
        self.adapter.assets.list_assets.assert_any_call('toolbitlibrary',store='local')
