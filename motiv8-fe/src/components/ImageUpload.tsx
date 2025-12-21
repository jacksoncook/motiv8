import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './ImageUpload.css';

const API_BASE_URL = 'http://localhost:8000';

interface UploadResponse {
  message: string;
  filename: string;
  embedding_filename: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  num_faces: number;
  bbox: number[];
  embedding_shape: number[];
  embedding_dtype: string;
}

interface GenerateResponse {
  message: string;
  generated_filename: string;
  embedding_filename: string;
  prompt: string;
}

function ImageUpload() {
  const { user, refreshUser } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateResult, setGenerateResult] = useState<GenerateResponse | null>(null);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [currentSelfieUrl, setCurrentSelfieUrl] = useState<string | null>(null);

  // Load current selfie if user has one
  useEffect(() => {
    if (user?.has_selfie && user.selfie_filename) {
      const token = localStorage.getItem('auth_token');
      setCurrentSelfieUrl(`${API_BASE_URL}/api/selfie/${user.selfie_filename}?token=${token}`);
    } else {
      setCurrentSelfieUrl(null);
    }
  }, [user]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      setUploadResult(null);

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const token = localStorage.getItem('auth_token');
      const response = await axios.post<UploadResponse>(
        `${API_BASE_URL}/api/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      setUploadResult(response.data);
      setSelectedFile(null);
      setPreviewUrl(null);

      // Refresh user data to get updated selfie information
      await refreshUser();

      // Update current selfie URL after successful upload
      if (response.data.filename) {
        setCurrentSelfieUrl(`${API_BASE_URL}/api/selfie/${response.data.filename}?token=${token}`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const handleGenerate = async () => {
    // Use uploadResult if available (just uploaded), otherwise use user's existing selfie
    const embeddingFilename = uploadResult?.embedding_filename || user?.selfie_embedding_filename;
    const imageFilename = uploadResult?.filename || user?.selfie_filename;

    if (!embeddingFilename) {
      setError('Please upload an image first');
      return;
    }

    setGenerating(true);
    setError(null);
    setGenerateResult(null);
    setGeneratedImageUrl(null);

    try {
      const token = localStorage.getItem('auth_token');
      const response = await axios.post<GenerateResponse>(
        `${API_BASE_URL}/api/generate`,
        {
          embedding_filename: embeddingFilename,
          image_filename: imageFilename,  // Pass original image for CLIP encoding
          prompt: "professional portrait photo of a person with extremely muscular bodybuilder physique, highly detailed, 8k, photorealistic",
          negative_prompt: "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality",
          num_inference_steps: 30,
          guidance_scale: 7.5,
          scale: 0.8
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      setGenerateResult(response.data);
      setGeneratedImageUrl(`${API_BASE_URL}/api/generated/${response.data.generated_filename}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Image generation failed. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="upload-container">
      {currentSelfieUrl && (
        <div className="current-selfie-section">
          <h3>Your Selfie</h3>
          <div className="preview-section">
            <img src={currentSelfieUrl} alt="Your selfie" className="preview-image" />
          </div>

          <div className="upload-section">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={uploading}
              id="file-input"
            />
            <label htmlFor="file-input" className="file-label">
              {selectedFile ? selectedFile.name : 'Choose an image'}
            </label>

            {previewUrl && (
              <div className="preview-section">
                <img src={previewUrl} alt="Preview" className="preview-image" />
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="upload-button"
            >
              {uploading ? 'Uploading...' : 'Update Selfie'}
            </button>
          </div>

          {user?.email === 'jacksoncook73@gmail.com' && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="upload-button generate-button"
            >
              {generating ? 'Generating Muscular Body Image...' : 'Generate Muscular Body Image'}
            </button>
          )}
        </div>
      )}

      {!currentSelfieUrl && (
        <div className="current-selfie-section">
          <h3>Your Selfie</h3>
          <div className="upload-section">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={uploading}
              id="file-input-initial"
            />
            <label htmlFor="file-input-initial" className="file-label">
              {selectedFile ? selectedFile.name : 'Choose an image'}
            </label>

            {previewUrl && (
              <div className="preview-section">
                <img src={previewUrl} alt="Preview" className="preview-image" />
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="upload-button"
            >
              {uploading ? 'Uploading...' : 'Upload Selfie'}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="message error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {uploadResult && (
        <div className="message success">
          <h3>Face Embedding Extracted!</h3>
          <p><strong>Original filename:</strong> {uploadResult.original_filename}</p>
          <p><strong>Image saved as:</strong> {uploadResult.filename}</p>
          <p><strong>Embedding saved as:</strong> {uploadResult.embedding_filename}</p>
          <p><strong>Faces detected:</strong> {uploadResult.num_faces}</p>
          <p><strong>Embedding shape:</strong> [{uploadResult.embedding_shape.join(', ')}]</p>
          <p><strong>Face bounding box:</strong> [{uploadResult.bbox.map(n => n.toFixed(1)).join(', ')}]</p>
          <p><strong>Type:</strong> {uploadResult.content_type}</p>
          <p><strong>Size:</strong> {formatFileSize(uploadResult.size_bytes)}</p>

          {user?.email === 'jacksoncook73@gmail.com' && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="upload-button generate-button"
            >
              {generating ? 'Generating Muscular Body Image...' : 'Generate Muscular Body Image'}
            </button>
          )}
        </div>
      )}

      {generatedImageUrl && (
        <div className="message success">
          <h3>Generated Image</h3>
          <div className="preview-section">
            <img src={generatedImageUrl} alt="Generated" className="preview-image" />
          </div>
          <p><strong>Generated filename:</strong> {generateResult?.generated_filename}</p>
          <p><strong>Prompt used:</strong> {generateResult?.prompt}</p>
        </div>
      )}
    </div>
  );
}

export default ImageUpload;
