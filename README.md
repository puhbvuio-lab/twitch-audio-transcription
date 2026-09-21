# Twitch 音频转写

这是一个独立运行的本地媒体与 Twitch VOD 音频处理工具。它会提取稳定的 16 kHz 单声道 WAV 音轨，使用 Faster-Whisper 进行语音转写，并从同一条规范时间线导出 JSON、CSV、SRT 和 VTT 文件。

本项目不会下载或分析弹幕，也不处理 CCV、画面、语义标签、频道历史或 Excel 报告。

## 环境要求

- Python 3.11 或更高版本。
- [FFmpeg](https://ffmpeg.org/) 已加入 `PATH`，用于提取和裁剪音频。
- `yt-dlp` 已加入 `PATH`，用于处理 Twitch VOD。
- Faster-Whisper 及其运行依赖，由项目安装配置提供。

安装项目：

```powershell
python -m pip install -e .
```

## 配置任务

项目提供两份不含凭据的示例配置：

- `examples/local-media-job.json`：处理本地视频或音频。
- `examples/vod-job.json`：下载并处理 Twitch VOD。

每个任务必须且只能配置一个输入：

- `media_path`：本地视频或音频文件路径。
- `vod_url`：Twitch VOD 地址。

其他主要字段：

- `start_seconds`、`end_seconds`：可选的分析时间范围，结束时间必须晚于开始时间。
- `output_dir`：任务输出根目录。
- `browser_cookie_source`：VOD 下载时可选的浏览器 Cookie 来源。
- `transcription_device`：设备策略，可设为 `auto`、`cuda` 或 `cpu`。
- `model_size`：Faster-Whisper 模型大小。
- `language`：指定语言；设为 `null` 时自动检测。

本地输入文件只会以只读方式访问，不会复制或修改。`browser_cookie_source` 只在调用 yt-dlp 时使用，不会写入配置快照、状态、错误或导出文件。

## 快速开始

使用本地媒体示例运行完整流程：

```powershell
python -m twitch_audio_transcription run --config examples/local-media-job.json
```

也可以分别执行各阶段：

```text
python -m twitch_audio_transcription acquire --config job.json
python -m twitch_audio_transcription extract-audio --config job.json
python -m twitch_audio_transcription transcribe --config job.json
python -m twitch_audio_transcription export --config job.json
python -m twitch_audio_transcription run --config job.json
```

各命令用途：

- `acquire`：验证本地媒体，或下载 Twitch VOD。
- `extract-audio`：生成 16 kHz 单声道分析音频。
- `transcribe`：运行 Faster-Whisper 并保存规范转写片段。
- `export`：从规范片段导出 JSON、CSV、SRT 和 VTT。
- `run`：按顺序执行完整流程；任一阶段失败后停止。

对于本地 `media_path`，`acquire` 阶段只记录来源元数据并标记为跳过下载。

## 时间范围

`start_seconds` 和 `end_seconds` 用于选择一个持续时间为正数的分析区间。输出的转写时间线始终从分析时间 `00:00:00` 开始，音频元数据则保留该区间相对于原始媒体的偏移量。

JSON、CSV、SRT 和 VTT 均由同一份规范转写片段生成，因此各格式中的开始和结束时间保持一致。

## 输出与断点续跑

产物位于 `<output_dir>/<job_id>/`：

- `01_source/`：来源元数据；VOD 任务还会保存下载的媒体。
- `02_audio/`：`analysis.wav` 及音频和裁剪元数据。
- `03_transcript/`：规范片段、运行信息以及 `转写结果.json`、`转写结果.csv`、`转写结果.srt`、`转写结果.vtt`。
- `09_status/`：各阶段状态、输入指纹、产物清单和错误摘要。

每个阶段都使用原子写入的输入指纹状态记录。只有输入匹配且预期产物完整时才会跳过已完成阶段，因此可以安全重试中断或失败的任务。

## 设备策略

`transcription_device` 支持：

- `auto`：先探测可用 CUDA；不可用时记录原因并回退 CPU。CUDA 运行时失败会再尝试一次 CPU。
- `cuda`：明确要求 CUDA；设备不可用时直接失败，不会伪装成 GPU 运行。
- `cpu`：始终使用 CPU。

实际选择的设备、计算类型和回退原因会写入转写运行信息及阶段状态。

## 测试

测试使用假的 FFmpeg、yt-dlp 和 Whisper 适配器，不会访问 Twitch、下载模型，也不要求 CUDA 或网络连接：

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q --basetemp=.pytest-tmp
```
