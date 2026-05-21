from __future__ import annotations

import re
from typing import Pattern


def _compile(pattern: str) -> Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


UNSUPPORTED_RULES: tuple[tuple[str, Pattern[str], str], ...] = (
    (
        "unsupported.file_delete_request",
        _compile(r"(删除|删掉|批量删掉|移除|清空).{0,16}(文件|文档|资料|知识库|目录|数据|记录|索引|向量库)"),
        "file_delete_request",
    ),
    (
        "unsupported.file_write_request",
        _compile(r"(修改|更新|覆盖|写入|替换|重置|重建).{0,16}(文件|文档|资料|知识库|目录|数据|记录|模板|配置|索引|向量库)"),
        "file_write_request",
    ),
    (
        "unsupported.kb_admin_request",
        _compile(r"(上传|导入|新增|新建|创建|重启).{0,16}(知识库|资料|文档|文件|服务|配置)"),
        "kb_admin_request",
    ),
    (
        "unsupported.privileged_operation",
        _compile(r"(权限授权|审批流程|管理员权限|权限变更|开通管理员|授予权限|登录生产|生产服务器)"),
        "privileged_operation",
    ),
    (
        "unsupported.unknown_external_action",
        _compile(r"(帮我操作|替我执行|调用外部系统|帮我登录|替我登录|直接改掉|强制重建)"),
        "unknown_external_action",
    ),
)
