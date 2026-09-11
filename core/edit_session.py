"""Independent per-object drafts and results. All jobs read source.cloud."""
from dataclasses import dataclass, replace
from pathlib import Path
from core.floor_manager import FloorManager
from core.pointcloud_processor import PreprocessingParams


@dataclass
class EditState:
    draft: PreprocessingParams = PreprocessingParams()
    saved_params: PreprocessingParams = PreprocessingParams()
    identity: object = None
    saved_identity: object = None
    preview: object = None
    preview_params: object = None
    saved_cloud: object = None
    saved_path: Path | None = None
    dirty: bool = False


class EditSession:
    def __init__(self):
        self.source = None
        self.manager = FloorManager()
        self.states = {None: EditState()}
        self.selected = None

    @property
    def current(self):
        return self.states[self.selected]

    def load(self, source):
        self.__init__()
        self.source = source

    def add_floor(self):
        if self.source is None:
            raise ValueError('请先加载完整 PCD。')
        floor = self.manager.create()
        self.states[floor.key] = EditState(identity=floor, saved_identity=floor, dirty=True)
        self.selected = floor.key
        return floor

    def edit(self, params, identity=None):
        state = self.current
        if state.draft != params or state.identity != identity:
            if state.draft != params:
                state.preview = state.preview_params = None
            state.draft, state.identity = params, identity
            state.dirty = (state.saved_path is None or params != state.saved_params or identity != state.saved_identity)

    def validate(self):
        self.current.draft.validate()
        if self.current.identity is not None:
            self.manager.validate(self.current.identity)

    def stage(self, cloud, params):
        if params != self.current.draft:
            raise ValueError('参数已改变，预览已过期。')
        self.current.preview, self.current.preview_params = cloud, params

    def export_ready(self):
        self.validate()
        state = self.current
        if state.identity is not None:
            state.identity.validate_for_export()
        if state.preview is None or state.preview_params != state.draft:
            raise ValueError('请先预览当前参数。')
        if not len(state.preview.points):
            raise ValueError('结果为空，不能保存。')

    def commit_saved(self, path):
        self.export_ready()
        state = self.current
        if state.identity is not None:
            floor = replace(state.identity, params=state.draft)
            self.manager.put(floor)
            state.identity = state.saved_identity = floor
        state.saved_params = state.draft
        state.saved_cloud = state.preview
        state.saved_path = Path(path)
        state.dirty = False

    def cancel(self):
        state = self.current
        state.draft, state.identity = state.saved_params, state.saved_identity
        state.preview = state.saved_cloud
        state.preview_params = state.saved_params if state.saved_cloud is not None else None
        state.dirty = state.saved_path is None and self.selected is not None

    def reset(self):
        params = PreprocessingParams()
        identity = replace(self.current.identity, params=params) if self.current.identity else None
        self.edit(params, identity)
        self.current.preview, self.current.preview_params = self.source.cloud, params

    def delete_selected(self):
        if self.selected is None:
            return
        self.manager.delete(self.selected)
        del self.states[self.selected]
        self.selected = None

    @property
    def has_unsaved(self):
        return any(state.dirty for state in self.states.values())
