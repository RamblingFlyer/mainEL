const canvas = document.createElement("canvas");
document.body.appendChild(canvas);
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const gl = canvas.getContext("webgl");
gl.enable(gl.DEPTH_TEST);

// ===== SHADERS =====
const vs = `
attribute vec3 position;
uniform mat4 mvp;
void main() {
  gl_Position = mvp * vec4(position, 1.0);
}
`;

const fs = `
void main() {
  gl_FragColor = vec4(0.8, 0.8, 0.8, 1.0);
}
`;

function compile(type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  return s;
}

const program = gl.createProgram();
gl.attachShader(program, compile(gl.VERTEX_SHADER, vs));
gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fs));
gl.linkProgram(program);
gl.useProgram(program);

// ===== FLOOR =====
const floor = new Float32Array([
  -50,0,-50,   50,0,-50,   50,0,50,
  -50,0,-50,   50,0,50,   -50,0,50
]);

const vbo = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
gl.bufferData(gl.ARRAY_BUFFER, floor, gl.STATIC_DRAW);

const posLoc = gl.getAttribLocation(program, "position");
gl.enableVertexAttribArray(posLoc);
gl.vertexAttribPointer(posLoc, 3, gl.FLOAT, false, 0, 0);

// ===== CAMERA =====
let camX = 0, camY = 1.6, camZ = 5;
let yaw = 0, pitch = 0;
const keys = {};

document.addEventListener("keydown", e => keys[e.key] = true);
document.addEventListener("keyup", e => keys[e.key] = false);

canvas.onclick = () => canvas.requestPointerLock();

document.addEventListener("mousemove", e => {
  if (document.pointerLockElement === canvas) {
    yaw -= e.movementX * 0.002;
    pitch -= e.movementY * 0.002;
    pitch = Math.max(-1.5, Math.min(1.5, pitch));
  }
});

// ===== MATH =====
function mat4Perspective(fov, aspect, near, far) {
  const f = 1 / Math.tan(fov/2);
  return [
    f/aspect,0,0,0,
    0,f,0,0,
    0,0,(far+near)/(near-far),-1,
    0,0,(2*far*near)/(near-far),0
  ];
}

function mat4Look() {
  const cx = Math.cos(pitch), sx = Math.sin(pitch);
  const cy = Math.cos(yaw), sy = Math.sin(yaw);

  const fx = sy*cx, fy = sx, fz = -cy*cx;

  return [
    cy,0,sy,0,
    sy*sx, cx, -cy*sx,0,
    -sy*cx, sx, cy*cx,0,
    -(camX*cy + camZ*sy),
    -(camY),
    -(-camX*sy*cx + camZ*cy*cx),
    1
  ];
}

// ===== LOOP =====
function loop() {
  const speed = 0.1;
  if (keys["w"]) { camX += Math.sin(yaw)*speed; camZ -= Math.cos(yaw)*speed; }
  if (keys["s"]) { camX -= Math.sin(yaw)*speed; camZ += Math.cos(yaw)*speed; }
  if (keys["a"]) { camX -= Math.cos(yaw)*speed; camZ -= Math.sin(yaw)*speed; }
  if (keys["d"]) { camX += Math.cos(yaw)*speed; camZ += Math.sin(yaw)*speed; }

  gl.clearColor(0.2,0.6,1.0,1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

  const proj = mat4Perspective(1.2, canvas.width/canvas.height, 0.1, 1000);
  const view = mat4Look();
  const mvp = proj.map((v,i)=>v+(view[i]||0));

  gl.uniformMatrix4fv(gl.getUniformLocation(program,"mvp"), false, mvp);
  gl.drawArrays(gl.TRIANGLES, 0, 6);

  requestAnimationFrame(loop);
}

loop();
