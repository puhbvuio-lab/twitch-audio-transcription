# Twitch Audio Transcription：设计规格

## 目标与边界

这是一个可独立复制和运行的音轨提取与语音转写项目。它从本地视频/音频，或可选的 Twitch VOD URL，提取标准化音轨并输出带时间戳的转写结果。

项目**不**获取或处理弹幕、不生成聊天标签/趋势、不输出 CCV/视觉/Excel 报告，也不依赖 `D:\主播基础分析`、`D:\twitch-video-chat-analysis` 或 `D:\twitch-chat-workflow` 的代码和数据。

成功标准：用户可用本地媒体文件或 VOD URL 运行任务，获得可断点续跑的 WAV、JSON、CSV、SRT/VTT 转写产物；优先使用 CUDA，无法使用时明确回退 CPU，不伪称使用 GPU。

## 输入与输出

### 输入

- 二选一必填：`media_path`（本地视频/音频）或 `vod_url`。
- 可选：`start_seconds`、`end_seconds`、`output_dir`、VOD 下载 Cookie 来源。
- 转写配置：模型大小、语言（可设为自动检测）、设备策略（`auto/cuda/cpu`）、计算类型、VAD 开关、批大小与线程数。

### 输出目录

每个任务位于 `<output_dir>/<job_id>/`：

- `01_source/`：来源元数据；若 URL 下载，保存下载媒体和下载状态。
- `02_audio/`：提取的规范音频（默认单声道 16 kHz WAV）、FFmpeg 元数据与切段信息。
- `03_transcript/`：完整 JSON、逐段 CSV、SRT、VTT，以及语言识别和运行元数据。
- `09_status/`：阶段状态、配置快照、日志、硬件探测与错误摘要。

## 架构

### 核心模块

1. `source`：验证本地媒体，或通过 `yt-dlp` 下载 VOD/目标片段。下载仅存在于本项目；本地媒体路径绝不复制或修改。
2. `audio_extract`：以 FFmpeg 产生稳定的 16 kHz 单声道 WAV；截取区间应用到音频，记录相对媒体与相对分析段时间。
3. `transcription`：封装 Faster-Whisper。`auto` 先检测 CUDA 和兼容计算类型，再选择 GPU；检测失败或运行失败后记录原因并回退 CPU。不得在未检测到 CUDA 时配置 CUDA。
4. `export`：从同一份逐段转写数据导出 JSON、CSV、SRT、VTT，保证所有格式的开始/结束时间一致。
5. `state`：按 source → audio → transcript → export 保存可恢复状态、输入指纹与产物清单。输入相同且产物完整时跳过完成步骤。
6. `cli`：分阶段命令和 `run` 总入口；不依赖弹幕项目的 CLI 或配置。

### 命令接口

```text
python -m twitch_audio_transcription acquire --config job.json
python -m twitch_audio_transcription extract-audio --config job.json
python -m twitch_audio_transcription transcribe --config job.json
python -m twitch_audio_transcription export --config job.json
python -m twitch_audio_transcription run --config job.json
```

对于本地 `media_path`，`acquire` 标记为 skipped；`run` 从 extract-audio 开始。对于 `vod_url`，`run` 先下载，再提取音频。

## 数据与错误处理原则

- 若用户提供本地文件，始终保留原文件，只读访问；中间文件仅写入任务输出目录。
- 不保证说话人身份，不输出未经证实的主播/观众角色结论。
- 保留每段文本、时间戳、语言、平均置信指标（引擎提供时）及转写配置。
- GPU/CUDA、FFmpeg、模型下载、URL 获取和格式错误分别记录；任何回退均可在状态文件和日志中见到。
- Cookie/令牌不进入配置快照、日志、命令回显或导出文件。

## 测试与验收

- 单元测试：配置验证、时间区间、转写段格式、SRT/VTT 时间格式化、状态恢复与设备策略选择。
- FFmpeg 集成测试：以短 fixture 生成 WAV 并校验采样率/声道数。
- 转写适配器测试：使用假的引擎响应，不下载模型、不要求 GPU。
- 验收检查：与弹幕项目没有 import、共享配置、共享目录或互相调用；只复制本项目目录并安装其自身依赖即可运行。
