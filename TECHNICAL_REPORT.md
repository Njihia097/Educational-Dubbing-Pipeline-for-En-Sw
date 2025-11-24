# **Technical Report: Educational English → Swahili Dubbing Pipeline**

**Project Type:** Final-Year AI/ML Project
**Date:** 2025
**Technologies:** Whisper, NLLB-200, LoRA, Docker, Flask, React, Celery, MinIO

---

# **1. Executive Summary**

This project delivers an **end-to-end educational video dubbing system** capable of converting English classroom videos into **Swahili-dubbed educational content**. The system integrates **ASR → MT → TTS → Audio Mixing → Video Re-assembly**, and includes a full web interface, job pipeline, and MinIO-based storage.

The core innovation is a **fine-tuned Machine Translation (MT) model** using **NLLB-200-600M + LoRA**, trained on high-quality English–Swahili educational data.

**Key MT result:**

* **BLEU:** **27.13**
* **chrF:** **52.09**
  (best performing checkpoint: *checkpoint-20000*)

The project demonstrates a fully functional translation pipeline, dataset handling, model training, evaluation, and deployment under a production-grade architecture.

---

# **2. Approach**

## **2.1 Data Preprocessing**

### **Initial Challenges**

* Raw OPUS Paracrawl dataset contained **inconsistent formatting**, **mixed domains**, and **noisy sentences**.
* Educational domain mismatch required additional **cleaning** and **length filtering**.
* Large dataset required **streaming preprocessing** to fit GPU memory limits.

### **Solutions**

* Extracted English–Swahili pairs from the `translation` field and removed empty/invalid rows.
* Standardized whitespace, removed markup and malformed entries.
* Implemented HuggingFace streaming generators for efficient handling of large corpora.
* Applied token-length truncation (**MAX SRC = 256**, **MAX TGT = 256**) for consistency.

### **Final Dataset**

After filtering:

* Approx. **20,000** parallel pairs per training epoch
* Evaluation slice: **2,000** pairs
* Domain: *general + educational*

---

## **2.2 Model Architecture (NLLB-600M + LoRA)**

### **Architecture**

Base model: **facebook/nllb-200-distilled-600M**
Components:

* Transformer encoder–decoder
* Language-specific BOS enforcement (`forced_bos_token_id = swh_Latn`)
* LoRA applied to:

  * `q_proj`, `k_proj`, `v_proj`, `out_proj`
  * `fc1`, `fc2`
* Only LoRA parameters + LM head stored (adapter-only training)

### **Key Hyperparameters**

| Hyperparameter        | Value         |
| --------------------- | ------------- |
| LoRA Rank             | 8             |
| LoRA Alpha            | 16            |
| LoRA Dropout          | 0.05          |
| LR                    | 2e-4          |
| Batch Size            | 64 (streamed) |
| Steps                 | 20k           |
| Generation Max Length | 256           |

### **Training Details**

* Loss: Cross-entropy
* Training strategy: **Iterative streaming dataset** through HF IterableDataset
* Scheduler: Linear warmup (`warmup_ratio=0.03`)
* FP16 acceleration enabled
* Checkpoints saved every 5,000 steps
* Evaluated via BLEU + chrF at same intervals

Total trainable parameters after LoRA: **~35M** (down from 600M full).

---

## **2.3 Evaluation Metrics**

* **BLEU:** Measures n-gram overlap
* **chrF:** Character n-gram F-score (more stable for morphologically rich Swahili)
* **Qualitative Sentence Checks:** Manual review for idiomatic correctness and educational tone

**Best results:**

* BLEU: **27.13**
* chrF: **52.09**

---

# **3. Results Summary**

## **3.1 Model Performance Comparison**

| Checkpoint | BLEU      | chrF      | Winner     |
| ---------- | --------- | --------- | ---------- |
| 10k        | 26.81     | 51.83     | –          |
| 15k        | 26.92     | 51.97     | –          |
| **20k**    | **27.13** | **52.09** | **Winner** |

---

## **3.2 Key Findings**

### **Strengths**

* Strong performance on general declarative educational sentences.
* Better handling of long-range dependencies after LoRA fine-tuning.
* Improved Swahili morphosyntax consistency compared to baseline NLLB.

### **Weaknesses**

* Occasional mistranslations in **context-heavy sentences**.
* Some literal translations remain (e.g., idioms or metaphors in teaching material).

---

# **4. Challenges Faced**

## **Pipeline Challenges**

### **1. Audio Artifacts (“Ghost Voices”)**

* **Issue:** Secondary audio injection due to duplicate FFmpeg mix streams.
* **Fix:** Explicitly mute original track before mixing.
* **Impact:** Cleaner dubbing output.

### **2. No Gender-Specific TTS Voices**

* **Issue:** XTTS/MMS lacked voice cloning for specific speakers.
* **Impact:** Robotic voice mismatch with original speakers.

### **4. MT Errors from Domain Mismatch**

* **Issue:** Educational tone not preserved consistently.
* **Solution:** Adapting a inferencing through user feedback loop.

### **5. Hardware Constraints**

* **Issue:** 8 GB GPU limited full-model training.
* **Solution:** LoRA enabled low-VRAM fine-tuning.
* **Impact:** Made training feasible but limited expressiveness.

---

# **5. Production Improvements**

## **5.1 Short-Term**

* Integrate Wav2Lip for true lipsync
* Improve ASR punctuation model

## **5.2 Medium-Term**

* Domain-adaptive training using elementary-school corpus
* Add voice-cloned TTS voices per speaker

## **5.3 Long-Term**

* Full active-learning pipeline (APE + QE)
* Multilingual expansion beyond Swahili
* Large-scale dataset curation + quality scoring

---

# **7. Conclusion**

This project successfully built a **complete English→Swahili educational video dubbing pipeline**, featuring a **fine-tuned MT model**, automated processing stages, real-time job tracking, and full deployment infrastructure.

The strongest achievement is the **NLLB-600M LoRA model** scoring **27.13 BLEU**, validating that domain-sensitive Swahili translation is feasible even with limited hardware.

**Next Step:**
Implement the feedback-driven MT improvement loop to continuously adapt the model to real user data.

---

# **8. Appendix**

### **Repository Structure **

```
/backend
    /app
    /utils
    /inference
/pipeline
    /mt
/notebooks
    mt_nllb_eval.ipynb
/models
    /finetuned
/env
```

### **Environment**

* OS: Windows 11 + WSL2 Ubuntu
* GPU: RTX 4060 (8 GB)
* RAM: 24 GB
* Frameworks: PyTorch, HF Transformers, LoRA, Flask, React


