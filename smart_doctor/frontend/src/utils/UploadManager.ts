/**
 * 分片上传管理器（v2.1 新增）
 *
 * 功能：
 * - 文件分片切割（默认 2MB/片）
 * - 并发上传控制（最多 3 片同时上传）
 * - 进度追踪与回调
 * - 断点续传（localStorage 保存 upload_id）
 * - 上传取消
 */
import api from "@/api";

export interface UploadProgress {
  uploadId: string;
  filename: string;
  totalChunks: number;
  uploadedChunks: number;
  percent: number;
  status: "init" | "uploading" | "completed" | "error" | "cancelled";
  error?: string;
}

export type ProgressCallback = (progress: UploadProgress) => void;

const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB
const MAX_CONCURRENT = 3;

export class UploadManager {
  private _abortControllers: Map<string, AbortController> = new Map();

  /**
   * 上传文件（含分片、断点续传）
   */
  async upload(
    file: File,
    doctorId: string,
    onProgress?: ProgressCallback
  ): Promise<UploadProgress> {
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    const fileExtension = file.name.split(".").pop()?.toLowerCase() || "txt";

    // Step 1: 初始化上传会话
    const initRes = await api.post("/knowledge/upload/init", {
      doctor_id: doctorId,
      filename: file.name,
      file_size: file.size,
      file_type: fileExtension,
      chunk_size: CHUNK_SIZE,
    });

    if (initRes.data.code !== 0) {
      throw new Error(initRes.data.message || "上传初始化失败");
    }

    const uploadId: string = initRes.data.data.upload_id;
    const totalChunksFromServer: number = initRes.data.data.total_chunks;

    // 保存到 localStorage 用于断点续传
    this._saveSession(uploadId, file.name, doctorId);

    const progress: UploadProgress = {
      uploadId,
      filename: file.name,
      totalChunks: totalChunksFromServer,
      uploadedChunks: 0,
      percent: 0,
      status: "uploading",
    };

    const abortController = new AbortController();
    this._abortControllers.set(uploadId, abortController);

    try {
      // Step 2: 并发上传分片
      await this._uploadChunks(
        file, uploadId, totalChunks, progress, onProgress, abortController.signal
      );

      // Step 3: 完成上传
      const completeRes = await api.post(`/knowledge/upload/${uploadId}/complete`);
      if (completeRes.data.code !== 0) {
        throw new Error(completeRes.data.message || "上传完成确认失败");
      }

      progress.status = "completed";
      progress.percent = 100;
      onProgress?.({ ...progress });

      // 清除会话记录
      this._clearSession(uploadId);
      return progress;
    } catch (err: any) {
      if (err.name === "AbortError" || err.message?.includes("abort")) {
        progress.status = "cancelled";
      } else {
        progress.status = "error";
        progress.error = err.message || "上传失败";
      }
      onProgress?.({ ...progress });
      throw err;
    }
  }

  /**
   * 并发上传所有分片
   */
  private async _uploadChunks(
    file: File,
    uploadId: string,
    totalChunks: number,
    progress: UploadProgress,
    onProgress?: ProgressCallback,
    signal?: AbortSignal,
  ): Promise<void> {
    const pending: number[] = [];
    for (let i = 0; i < totalChunks; i++) {
      pending.push(i);
    }

    let activeCount = 0;
    const errors: string[] = [];

    const uploadOne = async (chunkIndex: number): Promise<void> => {
      if (signal?.aborted) return;

      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const blob = file.slice(start, end);

      const formData = new FormData();
      formData.append("file", blob, `${chunkIndex}`);

      // 重试 3 次
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          await api.post(
            `/knowledge/upload/${uploadId}/chunk/${chunkIndex}`,
            formData,
            {
              headers: { "Content-Type": "multipart/form-data" },
              signal,
            }
          );

          progress.uploadedChunks++;
          progress.percent = Math.round(
            (progress.uploadedChunks / totalChunks) * 100
          );
          onProgress?.({ ...progress });
          return;
        } catch (err: any) {
          if (err.name === "AbortError") throw err;
          if (attempt === 2) {
            errors.push(`分片 ${chunkIndex} 上传失败`);
            throw new Error(errors.join("; "));
          }
          // 指数退避重试
          await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, attempt)));
        }
      }
    };

    return new Promise<void>((resolve, reject) => {
      const runNext = () => {
        if (signal?.aborted) {
          reject(new Error("Upload cancelled"));
          return;
        }

        while (activeCount < MAX_CONCURRENT && pending.length > 0) {
          const idx = pending.shift()!;
          activeCount++;
          uploadOne(idx)
            .then(() => {
              activeCount--;
              if (pending.length === 0 && activeCount === 0) {
                resolve();
              } else {
                runNext();
              }
            })
            .catch((err) => {
              reject(err);
            });
        }
      };

      runNext();
    });
  }

  /**
   * 取消上传
   */
  async cancel(uploadId: string): Promise<void> {
    const controller = this._abortControllers.get(uploadId);
    if (controller) {
      controller.abort();
      this._abortControllers.delete(uploadId);
    }
    try {
      await api.delete(`/knowledge/upload/${uploadId}`);
    } catch {
      // 忽略取消请求的错误
    }
    this._clearSession(uploadId);
  }

  /**
   * 查询上传状态（断点续传入口）
   */
  async getStatus(uploadId: string): Promise<UploadProgress | null> {
    try {
      const res = await api.get(`/knowledge/upload/${uploadId}/status`);
      if (res.data.code === 0) {
        const d = res.data.data;
        return {
          uploadId: d.upload_id,
          filename: d.filename,
          totalChunks: d.total_chunks,
          uploadedChunks: d.received_chunks,
          percent: d.progress_percent,
          status: d.status,
        };
      }
    } catch {
      // 会话不存在或已过期
    }
    return null;
  }

  private _saveSession(uploadId: string, filename: string, doctorId: string) {
    try {
      localStorage.setItem("upload_resume", JSON.stringify({
        uploadId, filename, doctorId, timestamp: Date.now(),
      }));
    } catch {
      // localStorage 不可用
    }
  }

  private _clearSession(uploadId: string) {
    try {
      const saved = localStorage.getItem("upload_resume");
      if (saved) {
        const data = JSON.parse(saved);
        if (data.uploadId === uploadId) {
          localStorage.removeItem("upload_resume");
        }
      }
    } catch {
      // ignore
    }
  }

  /**
   * 检查是否有可恢复的上传会话（30 分钟内）
   */
  static getResumableSession(): {
    uploadId: string; filename: string; doctorId: string;
  } | null {
    try {
      const saved = localStorage.getItem("upload_resume");
      if (!saved) return null;
      const data = JSON.parse(saved);
      if (Date.now() - data.timestamp > 30 * 60 * 1000) {
        localStorage.removeItem("upload_resume");
        return null;
      }
      return data;
    } catch {
      return null;
    }
  }
}
