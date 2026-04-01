import React from 'react';

export default function ModelUpload({ onModelLoaded }) {
  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    // Envia para o backend
    const formData = new FormData();
    formData.append('file', file);
    // Usar fetch com headers customizados para nome
    const res = await fetch('/upload/model', {
      method: 'POST',
      headers: { 'x-filename': encodeURIComponent(file.name) },
      body: file
    });
    if (res.ok) {
      const data = await res.json();
      if (data.url) {
        onModelLoaded(data.url);
      }
    } else {
      alert('Falha ao enviar modelo para o backend!');
    }
  };
  return (
    <div style={{ margin: '1rem 0' }}>
      <label style={{ fontWeight: 600 }}>Carregar modelo VRM:</label>
      <input type="file" accept=".vrm,.glb,.gltf" onChange={handleFile} />
    </div>
  );
}
