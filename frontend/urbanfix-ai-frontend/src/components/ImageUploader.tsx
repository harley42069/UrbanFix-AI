import React, { useState } from 'react';

const ImageUploader: React.FC<{ onImageUpload: (file: File) => void }> = ({ onImageUpload }) => {
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedImage(file);
            onImageUpload(file);
        }
    };

    const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file) {
            setSelectedImage(file);
            onImageUpload(file);
        }
        setIsDragging(false);
    };

    const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    return (
        <div
            className={`border-2 border-dashed rounded-lg p-4 ${isDragging ? 'border-blue-500' : 'border-gray-300'} transition-colors`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
        >
            <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
                id="image-upload"
            />
            <label htmlFor="image-upload" className="cursor-pointer text-center">
                {selectedImage ? (
                    <img src={URL.createObjectURL(selectedImage)} alt="Preview" className="w-full h-auto rounded-md" />
                ) : (
                    <p className="text-gray-500">Drag & drop an image here or click to upload</p>
                )}
            </label>
        </div>
    );
};

export default ImageUploader;