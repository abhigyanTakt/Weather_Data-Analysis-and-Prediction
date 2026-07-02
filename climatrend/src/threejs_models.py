"""
ClimaTrend Three.js 3D Weather Models.

This module provides HTML and Javascript templates to render animated 3D WebGL scenes
for different weather conditions using Three.js inside Streamlit components.
It supports both day and night visualization states.
"""

def get_3d_weather_model_html(weather_code: int, is_day: int = 1, label: str = "") -> str:
    """
    Returns the HTML/JS string containing a Three.js scene corresponding to the weather code and time of day.
    
    Weather codes mapping:
    - Clear (0): Sunny 3D rotating glowing sun (day) or silver glowing moon (night)
    - Cloudy / Fog (1, 2, 3, 45, 48): Fluffy floating clouds
    - Rainy / Drizzle / Showers (51-65, 80-82): Clouds with falling rain particles
    - Snowy (71-77, 85-86): Clouds with falling/drifting snow particles
    - Thunderstorm (95, 96, 99): Dark clouds with glowing lightning flashes
    """
    
    # Determine the general weather type
    if weather_code == 0:
        weather_type = "clear"
    elif weather_code in [1, 2, 3, 45, 48]:
        weather_type = "cloudy"
    elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
        weather_type = "rainy"
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        weather_type = "snowy"
    elif weather_code in [95, 96, 99]:
        weather_type = "thunderstorm"
    else:
        weather_type = "clear"

    if not label:
        label = "☀️ Daytime" if is_day == 1 else "🌙 Nighttime"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0;
                overflow: hidden;
                background-color: transparent;
                font-family: sans-serif;
            }}
            canvas {{
                display: block;
                width: 100vw;
                height: 100vh;
            }}
            #info {{
                position: absolute;
                bottom: 10px;
                width: 100%;
                text-align: center;
                color: #94a3b8;
                font-size: 11px;
                pointer-events: none;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
            }}
        </style>
        <!-- Load Three.js from a robust CDN -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    </head>
    <body>
        <div id="canvas-container"></div>
        <div id="info">Drag to rotate 3D model<br><span style="color:#00ffff; font-weight:bold; font-size:10px;">{label}</span></div>
        
        <script>
            const isDay = {is_day};
            
            // Initialize Scene, Camera, and Renderer
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
            camera.position.set(0, 0, 8);

            const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.shadowMap.enabled = true;
            document.getElementById('canvas-container').appendChild(renderer.domElement);

            // Add Lighting based on Day / Night
            let ambientLight, dirLight, pointLight;
            
            if (isDay === 1) {{
                // Daytime: Warm golden lighting
                ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
                scene.add(ambientLight);

                dirLight = new THREE.DirectionalLight(0xfffaed, 0.9);
                dirLight.position.set(5, 5, 5);
                scene.add(dirLight);

                pointLight = new THREE.PointLight(0xffa500, 0.6, 20);
                pointLight.position.set(0, 0, 4);
                scene.add(pointLight);
            }} else {{
                // Nighttime: Cool silver/cyan moonlight
                ambientLight = new THREE.AmbientLight(0x7dd3fc, 0.25);
                scene.add(ambientLight);

                dirLight = new THREE.DirectionalLight(0xe0f2fe, 0.5);
                dirLight.position.set(5, 5, 5);
                scene.add(dirLight);

                pointLight = new THREE.PointLight(0x38bdf8, 0.4, 20);
                pointLight.position.set(0, 0, 4);
                scene.add(pointLight);

                // Add background starry field for Nighttime
                const starsCount = 60;
                const starsGeom = new THREE.BufferGeometry();
                const starsPos = new Float32Array(starsCount * 3);
                for (let i = 0; i < starsCount; i++) {{
                    starsPos[i * 3] = (Math.random() - 0.5) * 12;
                    starsPos[i * 3 + 1] = (Math.random() - 0.5) * 12;
                    starsPos[i * 3 + 2] = (Math.random() - 0.5) * 6 - 4; // Render in background
                }}
                starsGeom.setAttribute('position', new THREE.BufferAttribute(starsPos, 3));
                const starsMat = new THREE.PointsMaterial({{
                    color: 0xffffff,
                    size: 0.04,
                    transparent: true,
                    opacity: 0.7
                }});
                const starsField = new THREE.Points(starsGeom, starsMat);
                scene.add(starsField);
            }}

            const weatherType = "{weather_type}";
            const group = new THREE.Group();
            scene.add(group);

            let particles, particleGeom;
            let lightningTime = 0;
            let thunderFlash = false;

            if (weatherType === "clear") {{
                if (isDay === 1) {{
                    // --- 3D SUN MODEL ---
                    const sunGeom = new THREE.SphereGeometry(1.5, 32, 32);
                    const sunMat = new THREE.MeshPhongMaterial({{
                        color: 0xffa500,
                        emissive: 0xff7700,
                        shininess: 100,
                    }});
                    const sunMesh = new THREE.Mesh(sunGeom, sunMat);
                    group.add(sunMesh);

                    // Glow Ring
                    const ringGeom = new THREE.TorusGeometry(2.0, 0.1, 16, 100);
                    const ringMat = new THREE.MeshBasicMaterial({{
                        color: 0xffea00,
                        transparent: true,
                        opacity: 0.6
                    }});
                    const ringMesh = new THREE.Mesh(ringGeom, ringMat);
                    group.add(ringMesh);

                    // Rays
                    const numRays = 8;
                    for (let i = 0; i < numRays; i++) {{
                        const rayGeom = new THREE.ConeGeometry(0.15, 0.8, 4);
                        const rayMat = new THREE.MeshPhongMaterial({{
                            color: 0xffd700,
                            emissive: 0xcc9900
                        }});
                        const ray = new THREE.Mesh(rayGeom, rayMat);
                        
                        const angle = (i / numRays) * Math.PI * 2;
                        ray.position.x = Math.cos(angle) * 2.2;
                        ray.position.y = Math.sin(angle) * 2.2;
                        ray.rotation.z = angle - Math.PI / 2;
                        group.add(ray);
                    }}
                }} else {{
                    // --- 3D MOON MODEL ---
                    const moonGeom = new THREE.SphereGeometry(1.4, 32, 32);
                    const moonMat = new THREE.MeshPhongMaterial({{
                        color: 0xe2e8f0,
                        emissive: 0x475569,
                        shininess: 30,
                        bumpScale: 0.05
                    }});
                    const moonMesh = new THREE.Mesh(moonGeom, moonMat);
                    group.add(moonMesh);

                    // Glowing Aura Ring
                    const auraGeom = new THREE.TorusGeometry(1.8, 0.08, 16, 100);
                    const auraMat = new THREE.MeshBasicMaterial({{
                        color: 0x7dd3fc,
                        transparent: true,
                        opacity: 0.4
                    }});
                    const auraMesh = new THREE.Mesh(auraGeom, auraMat);
                    group.add(auraMesh);

                    // Minor craters
                    const numCraters = 5;
                    const craterMat = new THREE.MeshPhongMaterial({{ color: 0xcbd5e1, flatShading: true }});
                    for (let i = 0; i < numCraters; i++) {{
                        const craterGeom = new THREE.SphereGeometry(0.2, 8, 8);
                        const crater = new THREE.Mesh(craterGeom, craterMat);
                        
                        const latAngle = (Math.random() - 0.5) * Math.PI;
                        const lonAngle = Math.random() * Math.PI * 2;
                        crater.position.x = Math.sin(lonAngle) * Math.cos(latAngle) * 1.35;
                        crater.position.y = Math.sin(latAngle) * 1.35;
                        crater.position.z = Math.cos(lonAngle) * Math.cos(latAngle) * 1.35;
                        group.add(crater);
                    }}
                }}

            }} else if (weatherType === "cloudy" || weatherType === "rainy" || weatherType === "snowy" || weatherType === "thunderstorm") {{
                // --- 3D CLOUD MODEL ---
                const cloudGroup = new THREE.Group();
                
                // Color cloud based on weather and time of day
                let cloudColor = 0xf8fafc; 
                if (isDay === 0) {{
                    cloudColor = 0x334155; // Dark night clouds
                }} else {{
                    if (weatherType === "rainy") cloudColor = 0xbac8d9;
                    if (weatherType === "snowy") cloudColor = 0xe2e8f0;
                    if (weatherType === "thunderstorm") cloudColor = 0x475569;
                }}

                const cloudMat = new THREE.MeshPhongMaterial({{
                    color: cloudColor,
                    emissive: (isDay === 0) ? 0x020617 : ((weatherType === "thunderstorm") ? 0x1e293b : 0x0f172a),
                    shininess: 10,
                    flatShading: true
                }});

                const spheres = [
                    {{ r: 1.0, x: 0, y: 0.5, z: 0 }},
                    {{ r: 0.8, x: -1.0, y: 0.2, z: 0.2 }},
                    {{ r: 0.8, x: 1.0, y: 0.2, z: -0.2 }},
                    {{ r: 0.6, x: -1.6, y: -0.1, z: 0.1 }},
                    {{ r: 0.6, x: 1.6, y: -0.1, z: -0.1 }},
                    {{ r: 0.7, x: 0.5, y: -0.2, z: 0.5 }},
                    {{ r: 0.7, x: -0.5, y: -0.2, z: 0.5 }}
                ];

                spheres.forEach(s => {{
                    const geom = new THREE.SphereGeometry(s.r, 8, 8);
                    const mesh = new THREE.Mesh(geom, cloudMat);
                    mesh.position.set(s.x, s.y, s.z);
                    cloudGroup.add(mesh);
                }});

                cloudGroup.position.y = 0.5;
                group.add(cloudGroup);

                // Add behind-the-cloud sun/moon peek
                if (weatherType === "cloudy") {{
                    if (isDay === 1) {{
                        const peekSun = new THREE.Mesh(
                            new THREE.SphereGeometry(0.7, 16, 16),
                            new THREE.MeshBasicMaterial({{ color: 0xffd700 }})
                        );
                        peekSun.position.set(-0.8, 1.2, -0.6);
                        group.add(peekSun);
                    }} else {{
                        const peekMoon = new THREE.Mesh(
                            new THREE.SphereGeometry(0.65, 16, 16),
                            new THREE.MeshBasicMaterial({{ color: 0xe2e8f0 }})
                        );
                        peekMoon.position.set(-0.8, 1.2, -0.6);
                        group.add(peekMoon);
                    }}
                }}

                // --- PARTICLES ---
                if (weatherType === "rainy" || weatherType === "thunderstorm") {{
                    const rainCount = 120;
                    particleGeom = new THREE.BufferGeometry();
                    const positions = new Float32Array(rainCount * 3);
                    const velocities = [];

                    for (let i = 0; i < rainCount; i++) {{
                        positions[i * 3] = (Math.random() - 0.5) * 3.5;
                        positions[i * 3 + 1] = Math.random() * 4 - 3;
                        positions[i * 3 + 2] = (Math.random() - 0.5) * 1.5;
                        velocities.push(0.1 + Math.random() * 0.1);
                    }}

                    particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

                    const rainMat = new THREE.PointsMaterial({{
                        color: (isDay === 1) ? 0x38bdf8 : 0x0284c7,
                        size: 0.08,
                        transparent: true,
                        opacity: 0.8
                    }});

                    particles = new THREE.Points(particleGeom, rainMat);
                    group.add(particles);
                    particles.velocities = velocities;

                }} else if (weatherType === "snowy") {{
                    const snowCount = 100;
                    particleGeom = new THREE.BufferGeometry();
                    const positions = new Float32Array(snowCount * 3);
                    const velocities = [];

                    for (let i = 0; i < snowCount; i++) {{
                        positions[i * 3] = (Math.random() - 0.5) * 3.5;
                        positions[i * 3 + 1] = Math.random() * 4 - 3;
                        positions[i * 3 + 2] = (Math.random() - 0.5) * 1.5;
                        velocities.push({{
                            y: 0.02 + Math.random() * 0.03,
                            x: (Math.random() - 0.5) * 0.01
                        }});
                    }}

                    particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));

                    const snowMat = new THREE.PointsMaterial({{
                        color: 0xffffff,
                        size: 0.1,
                        transparent: true,
                        opacity: 0.9
                    }});

                    particles = new THREE.Points(particleGeom, snowMat);
                    group.add(particles);
                    particles.velocities = velocities;
                }}
            }}

            // Mouse interaction / Auto-rotation variables
            let isDragging = false;
            let previousMousePosition = {{ x: 0, y: 0 }};

            window.addEventListener('mousedown', () => isDragging = true);
            window.addEventListener('mouseup', () => isDragging = false);
            window.addEventListener('mousemove', (e) => {{
                const deltaMove = {{
                    x: e.offsetX - previousMousePosition.x,
                    y: e.offsetY - previousMousePosition.y
                }};

                if (isDragging) {{
                    group.rotation.y += deltaMove.x * 0.01;
                    group.rotation.x += deltaMove.y * 0.01;
                }}

                previousMousePosition = {{
                    x: e.offsetX,
                    y: e.offsetY
                }};
            }});

            // Animation Loop
            function animate() {{
                requestAnimationFrame(animate);

                // Base auto rotation
                if (!isDragging) {{
                    group.rotation.y += 0.005;
                }}

                // Particle simulation (Rain/Snow)
                if (particles && particleGeom) {{
                    const positions = particleGeom.attributes.position.array;
                    
                    for (let i = 0; i < positions.length / 3; i++) {{
                        if (weatherType === "rainy" || weatherType === "thunderstorm") {{
                            positions[i * 3 + 1] -= particles.velocities[i];
                            if (positions[i * 3 + 1] < -3) {{
                                positions[i * 3 + 1] = 0.5;
                                positions[i * 3] = (Math.random() - 0.5) * 3.5;
                            }}
                        }} else if (weatherType === "snowy") {{
                            positions[i * 3 + 1] -= particles.velocities[i].y;
                            positions[i * 3] += Math.sin(Date.now() * 0.001 + i) * 0.005;
                            if (positions[i * 3 + 1] < -3) {{
                                positions[i * 3 + 1] = 0.5;
                                positions[i * 3] = (Math.random() - 0.5) * 3.5;
                            }}
                        }}
                    }}
                    particleGeom.attributes.position.needsUpdate = true;
                }}

                // Thunderstorm Lightning Simulation
                if (weatherType === "thunderstorm") {{
                    lightningTime += Math.random();
                    if (lightningTime > 30) {{
                        thunderFlash = true;
                        lightningTime = 0;
                    }}

                    if (thunderFlash) {{
                        ambientLight.intensity = (isDay === 1) ? 2.5 : 1.8;
                        dirLight.intensity = (isDay === 1) ? 2.0 : 1.5;
                        if (Math.random() > 0.7) {{
                            thunderFlash = false;
                        }}
                    }} else {{
                        ambientLight.intensity = (isDay === 1) ? 0.4 : 0.25;
                        dirLight.intensity = (isDay === 1) ? 0.6 : 0.35;
                    }}
                }}

                renderer.render(scene, camera);
            }}

            window.addEventListener('resize', () => {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }});

            animate();
        </script>
    </body>
    </html>
    """
    return html_template
