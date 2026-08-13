"""
企业级日志系统

提供结构化、可配置的日志基础设施，支持：
- JSON 格式输出（生产环境）
- 日志轮转（按天/大小）
- 请求追踪 ID（correlation_id）
- 上下文管理器
- 性能与慢查询日志
- 敏感信息脱敏
- 多输出目标（文件 + 控制台）
"""

import asyncio
import json
import os
import logging
import logging.handlers
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from app.core.config import settings

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

DEFAULT_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs",
)

# 敏感字段模式 -- 匹配日志中需要脱敏的键名
SENSITIVE_FIELDS: Set[str] = {
    "password", "passwd", "secret", "token", "access_token",
    "refresh_token", "api_key", "apikey", "api_secret", "secret_key",
    "authorization", "auth", "credential", "credit_card", "card_number",
    "cvv", "cvv2", "ssn", "phone", "phone_number", "mobile",
    "private_key", "private",
}

# 慢查询阈值（毫秒）
SLOW_QUERY_THRESHOLD_MS: int = 500

# 日志级别映射
LOG_LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# ---------------------------------------------------------------------------
# 敏感信息脱敏
# ---------------------------------------------------------------------------

# 匹配常见敏感字段值的正则（如 password=xxx 或 "password": "xxx"）
_SENSITIVE_VALUE_PATTERN = re.compile(
    r'(?i)((?:password|secret|token|api_key|authorization)\s*[:=]\s*)[\'"]?([^\'",\s}\]]+)[\'"]?'
)

# 匹配 JSON 中敏感键的值
_JSON_SENSITIVE_KEY_PATTERN = re.compile(
    r'(?i)"\s*(' + "|".join(re.escape(f) for f in SENSITIVE_FIELDS) + r')\s*"\s*:\s*"([^"]+)"'
)

# Token/Bearer 模式
_BEARER_PATTERN = re.compile(r'(?i)(Bearer\s+)[a-zA-Z0-9\-_.]+')
# 信用卡号模式
_CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
# 手机号模式（中国大陆）
_PHONE_PATTERN = re.compile(r'\b1[3-9]\d{9}\b')


def mask_sensitive(value: str, visible_chars: int = 4) -> str:
    """对敏感值进行脱敏处理，仅保留前 visible_chars 个字符。"""
    value = value.strip()
    if len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "****" + value[-1] if len(value) > visible_chars + 5 else value[:visible_chars] + "****"


def sanitize_message(message: str) -> str:
    """对日志消息中的敏感信息进行脱敏。"""
    # 脱敏 Bearer token
    message = _BEARER_PATTERN.sub(r'\1****', message)
    # 脱敏敏感值对
    message = _SENSITIVE_VALUE_PATTERN.sub(r'\1****', message)
    # 脱敏手机号
    message = _PHONE_PATTERN.sub(r'1********', message)
    # 脱敏信用卡号
    message = _CREDIT_CARD_PATTERN.sub(r'****', message)
    return message


def sanitize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """深度遍历日志记录，脱敏所有敏感字段。"""
    def _sanitize_value(key: str, value: Any) -> Any:
        if isinstance(value, str):
            if any(sf in key.lower() for sf in SENSITIVE_FIELDS):
                return mask_sensitive(value)
            return sanitize_message(value)
        if isinstance(value, dict):
            return {k: _sanitize_value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [_sanitize_value(key, item) if isinstance(item, (dict, str)) else item for item in value]
        return value

    return {k: _sanitize_value(k, v) for k, v in record.items()}


# ---------------------------------------------------------------------------
# JSON 日志格式化器
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """将日志记录输出为 JSON 格式，适合生产环境日志收集。"""

    def __init__(
        self,
        include_traceback: bool = True,
        ensure_ascii: bool = False,
        **fmt_kwargs: Any,
    ) -> None:
        super().__init__(**fmt_kwargs)
        self.include_traceback = include_traceback
        self.ensure_ascii = ensure_ascii

    def format(self, record: logging.LogRecord) -> str:
        # 构建基础日志条目
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage() if record.args else record.msg,
            "process": record.process,
            "thread": record.thread,
        }

        # 异常信息
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)) if self.include_traceback else None,
            }

        # 额外上下文（extra 属性）
        extra_keys = {
            k for k in dir(record) if not k.startswith("_")
            and k not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "message", "module", "msecs", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName",
            }
        }
        for key in extra_keys:
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        # 脱敏
        log_entry = sanitize_record(log_entry)

        # 添加 correlation_id 的兼容处理
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        elif "correlation_id" not in log_entry:
            log_entry["correlation_id"] = None

        return json.dumps(log_entry, ensure_ascii=self.ensure_ascii, default=str)


# ---------------------------------------------------------------------------
# 可读文本格式化器（开发环境）
# ---------------------------------------------------------------------------

class TextFormatter(logging.Formatter):
    """人类可读的彩色日志格式化器（开发环境使用）。"""

    # ANSI 颜色码
    _LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",      # 青色
        logging.INFO: "\033[32m",       # 绿色
        logging.WARNING: "\033[33m",    # 黄色
        logging.ERROR: "\033[31m",      # 红色
        logging.CRITICAL: "\033[41m",   # 红底白字
    }
    _RESET = "\033[0m"
    _BOLD = "\033[1m"

    def __init__(self, use_colors: bool = True, **fmt_kwargs: Any) -> None:
        if not fmt_kwargs:
            fmt_kwargs["fmt"] = (
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
            fmt_kwargs["datefmt"] = "%Y-%m-%d %H:%M:%S"
        super().__init__(**fmt_kwargs)
        self.use_colors = use_colors and sys.platform != "win32"

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.getMessage()
        # 脱敏
        safe_msg = sanitize_message(original_msg)
        record.msg = safe_msg
        record.args = ()  # 已格式化，清除参数

        # 时间
        asctime = self.formatTime(record, self.datefmt)

        # 级别
        levelname = record.levelname
        if self.use_colors:
            color = self._LEVEL_COLORS.get(record.levelno, self._RESET)
            levelname = f"{color}{levelname}{self._RESET}"

        # 名称
        name = record.name
        if self.use_colors:
            name = f"{self._BOLD}{name}{self._RESET}"

        # 关联 ID
        corr_id = getattr(record, "correlation_id", None) or ""
        corr_str = f" [{corr_id}]" if corr_id else ""

        # 模块定位
        location = f"{record.pathname}:{record.lineno}" if record.levelno >= logging.WARNING else ""

        # 异常
        exc_text = ""
        if record.exc_info and record.exc_info[0] is not None:
            exc_text = "\n" + "".join(traceback.format_exception(*record.exc_info))

        if location:
            return f"{asctime} | {levelname} | {name}{corr_str} | {safe_msg} ({location}){exc_text}"
        return f"{asctime} | {levelname} | {name}{corr_str} | {safe_msg}{exc_text}"


# ---------------------------------------------------------------------------
# 日志上下文 - 请求追踪 ID
# ---------------------------------------------------------------------------

# 线程/协程局部存储用 contextvars
import contextvars

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def set_correlation_id(cid: str) -> None:
    """设置当前上下文的请求追踪 ID。"""
    _correlation_id_var.set(cid)


def get_correlation_id() -> str:
    """获取当前上下文的请求追踪 ID。"""
    return _correlation_id_var.get()


def generate_correlation_id() -> str:
    """生成新的请求追踪 ID。"""
    return uuid4().hex[:16]


# ---------------------------------------------------------------------------
# 日志上下文管理器
# ---------------------------------------------------------------------------

class LoggerContext:
    """日志上下文管理器，为代码块添加关联 ID 和额外标签。

    用法::

        with LoggerContext(correlation_id="req-123", user_id=42) as ctx:
            ctx.logger.info("处理用户请求")
            # 所有日志自动携带 correlation_id 和 user_id
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        logger_name: str = "manga",
        **extra_tags: Any,
    ) -> None:
        self.correlation_id = correlation_id or generate_correlation_id()
        self.extra_tags = extra_tags
        self.logger = logging.getLogger(logger_name)
        self._old_cid: str = ""
        self._extra_attrs: Dict[str, Any] = {}

    def __enter__(self) -> "LoggerContext":
        self._old_cid = get_correlation_id()
        set_correlation_id(self.correlation_id)
        # 保存额外的日志属性
        self._extra_attrs = {
            "correlation_id": self.correlation_id,
            **self.extra_tags,
        }
        # 通过 logging.LoggerAdapter 或直接使用 extra 参数
        self.logger = logging.LoggerAdapter(
            self.logger,
            self._extra_attrs,
        )
        return self

    def __exit__(self, *args: Any) -> None:
        # 恢复旧的 correlation_id
        set_correlation_id(self._old_cid)

    def get_extra(self) -> Dict[str, Any]:
        return self._extra_attrs.copy()


# ---------------------------------------------------------------------------
# 性能日志记录
# ---------------------------------------------------------------------------

class PerformanceLogger:
    """性能日志记录器，用于测量代码块执行时间。

    用法::

        perf = PerformanceLogger("db_query")
        with perf:
            result = await db.fetch(query)
        # 自动记录耗时 > 500ms 的慢查询
    """

    def __init__(
        self,
        operation: str,
        threshold_ms: int = SLOW_QUERY_THRESHOLD_MS,
        logger_name: str = "manga.performance",
        **context: Any,
    ) -> None:
        self.operation = operation
        self.threshold_ms = threshold_ms
        self.logger = logging.getLogger(logger_name)
        self.context = context
        self.start_time: float = 0.0
        self.duration_ms: float = 0.0

    def __enter__(self) -> "PerformanceLogger":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000
        extra: Dict[str, Any] = {
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 2),
            "correlation_id": get_correlation_id(),
            **self.context,
        }
        if exc_type is not None:
            extra["error"] = str(exc_val)
            extra["error_type"] = exc_type.__name__

        if self.duration_ms >= self.threshold_ms:
            # 慢操作 -- 记录 WARNING
            self.logger.warning(
                "慢操作 [%s] 耗时 %.2fms (阈值: %dms)",
                self.operation, self.duration_ms, self.threshold_ms,
                extra=extra,
            )
        else:
            self.logger.info(
                "操作 [%s] 耗时 %.2fms",
                self.operation, self.duration_ms,
                extra=extra,
            )


# ---------------------------------------------------------------------------
# 慢查询日志装饰器
# ---------------------------------------------------------------------------

def log_slow_query(
    threshold_ms: int = SLOW_QUERY_THRESHOLD_MS,
    logger_name: str = "manga.db.slow",
) -> Any:
    """装饰器：记录数据库查询的执行时间，超过阈值自动告警。

    用法::

        @log_slow_query(threshold_ms=300)
        async def get_users() -> List[User]:
            ...
    """
    def decorator(func: Any) -> Any:
        import functools
        logger = logging.getLogger(logger_name)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                extra: Dict[str, Any] = {
                    "operation": func.__qualname__,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
                if duration_ms >= threshold_ms:
                    logger.warning(
                        "慢查询 [%s] 耗时 %.2fms (阈值: %dms)",
                        func.__qualname__, duration_ms, threshold_ms,
                        extra=extra,
                    )
                else:
                    logger.debug(
                        "查询 [%s] 耗时 %.2fms",
                        func.__qualname__, duration_ms,
                        extra=extra,
                    )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                extra: Dict[str, Any] = {
                    "operation": func.__qualname__,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": get_correlation_id(),
                }
                if duration_ms >= threshold_ms:
                    logger.warning(
                        "慢查询 [%s] 耗时 %.2fms (阈值: %dms)",
                        func.__qualname__, duration_ms, threshold_ms,
                        extra=extra,
                    )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# 日志过滤器 - 敏感信息
# ---------------------------------------------------------------------------

class SensitiveDataFilter(logging.Filter):
    """日志过滤器，在 LogRecord 层面过滤敏感信息。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_message(record.msg)
        return True


# ---------------------------------------------------------------------------
# 日志过滤器 - 级别阈值
# ---------------------------------------------------------------------------

class LevelFilter(logging.Filter):
    """只允许指定级别范围内的日志通过。"""

    def __init__(self, min_level: int = logging.DEBUG, max_level: int = logging.CRITICAL) -> None:
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return self.min_level <= record.levelno <= self.max_level


# ---------------------------------------------------------------------------
# 日志初始化
# ---------------------------------------------------------------------------

def _get_log_level() -> int:
    """从配置获取日志级别。"""
    env_level = settings.DEBUG and "DEBUG" or "INFO"
    return LOG_LEVEL_MAP.get(env_level, logging.INFO)


def _ensure_log_dir(log_dir: str) -> str:
    """确保日志目录存在。"""
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _setup_console_handler(
    formatter: logging.Formatter,
    level: int,
) -> logging.Handler:
    """配置控制台输出处理器。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())
    return handler


def _setup_file_handler(
    log_dir: str,
    filename: str,
    formatter: logging.Formatter,
    level: int,
    when: str = "midnight",
    backup_count: int = 30,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
) -> logging.Handler:
    """配置文件输出处理器（按天轮转 + 大小限制）。"""
    log_path = os.path.join(log_dir, filename)
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_path,
        when=when,
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
        delay=False,
    )
    # 同时添加大小轮转作为补充
    # 使用 RotatingFileHandler 兜底
    handler = logging.handlers.RotatingFileHandler(
        filename=log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=False,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())
    return handler


# ---------------------------------------------------------------------------
# 模块级日志获取函数
# ---------------------------------------------------------------------------

_loggers_configured: bool = False


def configure_logging(
    log_dir: Optional[str] = None,
    level: Optional[Union[str, int]] = None,
    enable_json: Optional[bool] = None,
    enable_file: bool = True,
    enable_console: bool = True,
) -> None:
    """全局日志配置（应在应用启动时调用一次）。

    Args:
        log_dir: 日志文件目录，默认 ./logs
        level: 日志级别，默认从 settings.DEBUG 推断
        enable_json: 是否输出 JSON 格式（生产环境建议 True），默认根据 ENV 判断
        enable_file: 是否输出到文件
        enable_console: 是否输出到控制台
    """
    global _loggers_configured

    log_dir = log_dir or _ensure_log_dir(DEFAULT_LOG_DIR)
    log_level = LOG_LEVEL_MAP.get(level.upper()) if isinstance(level, str) else (level or _get_log_level())
    is_production = settings.ENV == "production"
    use_json = enable_json if enable_json is not None else is_production

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有处理器（避免重复配置）
    root_logger.handlers.clear()

    # ---- 格式化器 ----
    if use_json:
        console_formatter = JSONFormatter()
        file_formatter = JSONFormatter()
    else:
        console_formatter = TextFormatter(use_colors=True)
        file_formatter = TextFormatter(use_colors=False)

    # ---- 控制台 ----
    if enable_console:
        console_handler = _setup_console_handler(console_formatter, log_level)
        root_logger.addHandler(console_handler)

    # ---- 文件 ----
    if enable_file:
        # 通用日志
        file_handler = _setup_file_handler(log_dir, "app.log", file_formatter, log_level)
        root_logger.addHandler(file_handler)

        # 错误日志（仅 ERROR 及以上）
        error_handler = _setup_file_handler(
            log_dir, "error.log", file_formatter, logging.ERROR,
        )
        root_logger.addHandler(error_handler)

        # JSON 日志（生产环境独立文件）
        if use_json:
            json_handler = _setup_file_handler(
                log_dir, "app.json.log", JSONFormatter(), log_level,
            )
            root_logger.addHandler(json_handler)

        # 慢查询日志
        slow_handler = _setup_file_handler(
            log_dir, "slow.log", file_formatter, logging.WARNING,
        )
        slow_handler.addFilter(LevelFilter(min_level=logging.WARNING))
        slow_logger = logging.getLogger("manga.db.slow")
        slow_logger.handlers.clear()
        slow_logger.addHandler(slow_handler)
        slow_logger.setLevel(logging.WARNING)

        # 性能日志
        perf_handler = _setup_file_handler(
            log_dir, "performance.log", file_formatter, logging.INFO,
        )
        perf_logger = logging.getLogger("manga.performance")
        perf_logger.handlers.clear()
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)

    _loggers_configured = True
    logger = logging.getLogger("manga")
    logger.info(
        "日志系统初始化完成: level=%s, json=%s, dir=%s",
        logging.getLevelName(log_level), use_json, log_dir,
    )


def get_logger(name: str = "manga") -> logging.Logger:
    """获取日志器实例。

    在模块级别使用::

        logger = get_logger(__name__)
        logger.info("hello")
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def log_exception(logger: logging.Logger, exc: Exception, message: str = "未捕获异常") -> None:
    """统一记录异常日志。"""
    logger.error(
        "%s: %s - %s",
        message, type(exc).__name__, str(exc),
        exc_info=True,
    )


def log_request_summary(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra: Any,
) -> None:
    """记录请求摘要。"""
    extra_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "correlation_id": get_correlation_id(),
        **extra,
    }
    logger.info(
        "%s %s -> %d (%.2fms)",
        method, path, status_code, duration_ms,
        extra=extra_data,
    )