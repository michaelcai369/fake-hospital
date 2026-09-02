# ResidentScribe V1

一个仅生成草稿的中文问诊病历辅助工具：录音或上传音频，调用阿里云百炼的 Qwen3-ASR 转写，再由千问将已转录内容整理为结构化病历草稿。全流程只需要一把百炼 API Key。

> **安全边界**：本项目仅适合教学、模拟或已取得必要授权的临床辅助。它不提供诊断、处方或治疗建议，不保存病历，也绝不能替代医生审核和签署。不要上传姓名、证件号、手机号、住院号等可识别信息；真实使用前应遵守所在机构的录音、隐私与数据合规规定。

## V1 功能

- 麦克风录音或上传常见音频文件
- 中文语音转录（百炼 `qwen3-asr-flash`；单段不超过 5 分钟、10 MB）
- 病历草稿生成（百炼 `qwen-plus`）
- 可编辑的转录文本，随后再生成草稿
- 固定的中文入院病历栏目与“遗漏问诊提醒”
- 对手机号、身份证号、常见就诊编号进行发送前掩码（非完整去标识化）
- 下载草稿；不设置数据库、不接入 HIS/EMR、不将数据持久化

## 本地启动

需要 Python 3.10 或更新版本。

```bash
cd resident-scribe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

编辑 `.streamlit/secrets.toml`，填写自己的 `DASHSCOPE_API_KEY`。该文件已被 `.gitignore` 排除，**绝不可提交到 Git**。请使用已开通 `qwen3-asr-flash` 和 `qwen-plus` 模型权限的北京地域百炼 Key。

启动后浏览器会打开 `http://localhost:8501`。先使用模拟问诊验证整条链路，再考虑任何临床场景。

## 推荐的模拟测试

录制或上传以下语音：

> 医生：哪里不舒服？患者：右上腹疼了两个多月。医生：什么时候更明显？患者：吃完油腻的东西更明显。医生：有没有发烧？患者：没有。医生：恶心、呕吐呢？患者：偶尔有点恶心，没有吐。

预期结果必须体现：右上腹疼痛两月余、油腻饮食后明显、偶有恶心、明确无发热/无呕吐；未问及的黄疸、放射痛等只能标为“未询及”或放入遗漏提醒，不能变成阴性结论。

## 项目结构

```text
resident-scribe/
├── app.py              # Streamlit UI 与临时会话状态
├── bailian_stt.py      # 百炼音频转写
├── medical_note.py     # 病历草稿生成
├── prompts.py          # 安全约束与固定病历模板
├── requirements.txt
└── .streamlit/
    └── secrets.toml.example
```

## 下一阶段（不在 V1 范围内）

1. 使用合成/脱敏的测试集，评估转写错误、否定词错误和病历虚构率。
2. 按轮转科室增加**人工审查过**的模板，且保持“未询及不等于否认”。
3. 若机构批准后再考虑本地模型、角色分离与实时辅助；HIS/EMR 接入需要单独的安全、审计和审批设计。
