import React from 'react';

export default function AnimationControls({ onAnimationChange, onPoseChange }) {
    const animations = ['Idle', 'Walk', 'Dance'];
    const poses = ['Neutral', 'Wave', 'Think'];

    return (
        <div className="control-panel">
            <h3>Animations & Poses</h3>

            <div className="control-group">
                <h4>Animations</h4>
                <div className="button-grid">
                    {animations.map(anim => (
                        <button key={anim} onClick={() => onAnimationChange(anim)}>
                            {anim}
                        </button>
                    ))}
                    <label className="file-upload">
                        Load FBX
                        <input type="file" accept=".fbx" onChange={async (e) => {
                            const file = e.target.files[0];
                            if (file) {
                                // Envia para o backend
                                const res = await fetch('/upload/animation', {
                                    method: 'POST',
                                    headers: { 'x-filename': encodeURIComponent(file.name) },
                                    body: file
                                });
                                if (res.ok) {
                                    const data = await res.json();
                                    if (data.url) {
                                        onAnimationChange({ name: file.name, url: data.url });
                                    }
                                } else {
                                    alert('Falha ao enviar animação para o backend!');
                                }
                            }
                        }} />
                    </label>
                </div>
            </div>

            <div className="control-group">
                <h4>Poses</h4>
                <div className="button-grid">
                    {poses.map(pose => (
                        <button key={pose} onClick={() => onPoseChange(pose)}>
                            {pose}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
