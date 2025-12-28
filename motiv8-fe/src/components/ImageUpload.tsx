import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './ImageUpload.css';

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || "https://api.motiv8me.io";

interface UploadResponse {
  message: string;
  filename: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  is_update: boolean;
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
  const [canGenerate, setCanGenerate] = useState(false);
  const [isProduction, setIsProduction] = useState(true);

  // Check if on-demand generation is enabled and get environment
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/config`);
        setCanGenerate(response.data.features.onDemandGeneration);
        setIsProduction(response.data.environment === 'production');
      } catch (error) {
        console.error('Failed to fetch config:', error);
        // Default to production mode in case of error
        setCanGenerate(false);
        setIsProduction(true);
      }
    };
    fetchConfig();
  }, []);

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

  const handleGenerate = async () => {
    // Use user's existing selfie (embedding is created by batch job)
    const embeddingFilename = user?.selfie_embedding_filename;
    const imageFilename = user?.selfie_filename;

    if (!embeddingFilename) {
      setError('Please wait for face extraction to complete before generating images');
      return;
    }

    setGenerating(true);
    setError(null);
    setGenerateResult(null);
    setGeneratedImageUrl(null);

    try {
      const token = localStorage.getItem('auth_token');
      // Generate a random seed for variation in results
      const randomSeed = Math.floor(Math.random() * 1000000);

      // Create gender-specific prompt
      const genderTerm = user?.gender === "female" ? "female" : "male";
      const prompt = `professional full body photo of a ${genderTerm} bodybuilder with extremely muscular physique, highly detailed, 8k, photorealistic`;

      const response = await axios.post<GenerateResponse>(
        `${API_BASE_URL}/api/generate`,
        {
          embedding_filename: embeddingFilename,
          image_filename: imageFilename,  // Pass original image for CLIP encoding
          prompt: prompt,
          negative_prompt: "blurry, low quality, distorted, deformed, ugly, bad anatomy, monochrome, lowres, bad anatomy, worst quality, low quality",
          num_inference_steps: 30,
          guidance_scale: 7.5,
          scale: 0.8,
          seed: randomSeed
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
          <h3>Your selfie</h3>
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
              {uploading ? 'Uploading...' : 'Update selfie'}
            </button>
          </div>

          {canGenerate && user?.email === 'jacksoncook73@gmail.com' && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="upload-button generate-button"
            >
              {generating ? 'Generating muscular body image...' : 'Generate muscular body image'}
            </button>
          )}
        </div>
      )}

      {!currentSelfieUrl && (
        <div className="current-selfie-section">
          <h3>Your selfie</h3>
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
              {uploading ? 'Uploading...' : 'Upload selfie'}
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
          <h3>Selfie uploaded successfully!</h3>
          {!isProduction && (
            <>
              <p>{uploadResult.message}</p>
              <p><strong>Original filename:</strong> {uploadResult.original_filename}</p>
              <p><strong>File size:</strong> {(uploadResult.size_bytes / 1024).toFixed(2)} KB</p>
              <p className="info-text">Face extraction will occur during the next batch processing run.</p>
            </>
          )}

          {canGenerate && user?.email === 'jacksoncook73@gmail.com' && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="upload-button generate-button"
            >
              {generating ? 'Generating muscular body image...' : 'Generate muscular body image'}
            </button>
          )}
        </div>
      )}

      {generatedImageUrl && (
        <div className="message success">
          <h3>Generated image</h3>
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
