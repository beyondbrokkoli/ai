/home/halim/llama.cpp/build/bin/llama-server \
  -m /home/halim/Downloads/nomic-embed-text-v1.5.f32.gguf \
  --host 10.0.0.2 \
  --port 8081 \
  --embedding \
  --pooling mean \
  -c 2048 \
  -t 6 \
  --api-key TEST1234
