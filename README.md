# 🎬 FFmpeg Multi Downloader

Interface visual moderna, elegante e poderosa para baixar múltiplos vídeos, músicas, playlists completas, transmissões em stream (.m3u8 / HLS), links diretos (.mp4, .ts) e vídeos da web simultaneamente usando **FFmpeg** e **yt-dlp**.

---

## 📦 Instalador Oficial para Windows (.exe)

O aplicativo conta com instalador executável completo e profissional:
- **`Instalador_FFmpeg_Downloader.exe`**: Dê duplo clique para instalar no seu Windows.
  - ✅ Cria automaticamente o **atalho na Área de Trabalho** com ícone personalizado.
  - ✅ Cria entrada no **Menu Iniciar** do Windows.
  - ✅ Já inclui todos os binários portáteis (**FFmpeg 9.0 Full**, **FFprobe** e **yt-dlp**) integrados.
  - ✅ Não requer Python instalado para os usuários finais.
  - ✅ Inclui assistente de desinstalação completo no Painel de Controle do Windows.

---

## ✨ Recursos Principais

### 1. 🎵 Capas de Álbum e Metadados Automáticos (ID3 Tags)
- **Thumbnail / Capa embutida**: Ao baixar músicas (MP3, M4A, FLAC, OPUS), a arte da capa do álbum/vídeo é embutida diretamente dentro do arquivo.
- **Tags completas**: Preenche automaticamente Artista, Título da Música, Álbum e Ano no arquivo (via `mutagen`). Ao abrir no celular, carro, Spotify ou Windows Media Player, a capa e todas as informações já aparecem prontas!

### 2. 🖼️ Miniatura (Thumbnail) Visual nos Cards da Fila
- Cada item na fila exibe a miniatura real do vídeo/música em alta definição com cantos arredondados, trazendo uma experiência visual de alto nível.

### 3. 📋 Monitor de Área de Transferência (Clipboard Auto-Detect)
- Opção `📋 Monitorar Copiar/Colar (Ctrl+C)`: ao copiar qualquer link de vídeo ou música no seu navegador, o programa detecta instantaneamente e adiciona o link na caixa de entrada sem você precisar trocar de janela para colar.

### 4. 📝 Download e Embutimento de Legendas (.srt / Embutidas)
- Baixa legendas oficiais e legendas geradas automaticamente por IA (auto-subs do YouTube).
- Opção de salvar como arquivo `.srt` separado ou já embutir diretamente dentro do vídeo (`.mp4` / `.mkv`).
- Filtro por idioma: Português (pt), Inglês (en) ou Todos os idiomas disponíveis.

### 5. 📂 Expansão Inteligente de Playlists
- Ao colar o link de uma Playlist do YouTube ou álbum:
  - O programa desmembra automaticamente cada vídeo em uma tarefa individual na fila, com títulos e miniaturas individuais.

### 6. 🔔 Notificação Nativa do Windows ao Concluir
- Quando todos os downloads terminam (mesmo com o app minimizado enquanto você joga ou estuda), o Windows exibe uma notificação nativa com alerta sonoro. Ao clicar na notificação, a pasta de downloads abre imediatamente.

### 7. 🌐 Autenticação e Login de Navegadores (Cookies)
- Permite baixar de sites com login ativo (YouTube Music, portais fechados, vídeos privados):
  - Suporte direto a **Google Chrome**, **Microsoft Edge**, **Mozilla Firefox** e **Brave**.
  - Suporte a arquivo **`cookies.txt`** para plataformas protegidas por Cloudflare.
  - Campo expansível para **Headers HTTP** (`Referer` e `User-Agent`) para plataformas de cursos fechados (Hotmart, Kiwify, Panda Video).

### 8. 🎛️ Formatos e Qualidades Suportados
- **Vídeo**: MP4, MKV, TS (1080p Full HD, 720p HD, 480p, 360p ou Melhor Qualidade).
- **Música**:
  - **MP3** (128 kbps até 320 kbps)
  - **FLAC** (Lossless / Sem perdas de qualidade)
  - **WAV** (Áudio PCM de estúdio sem compressão)
  - **M4A** (AAC)
  - **OPUS** (Áudio original do YouTube sem reconversão)

---

## 🚀 Como Iniciar (Modo Portátil sem instalar)

Se preferir rodar diretamente da pasta do código sem executar o instalador:
- **`FFmpeg Downloader.lnk`** (Atalho nativo com ícone — inicia silenciosamente sem janela preta)
- **`Iniciar_Sem_Janela_Preta.bat`** (Inicia o app em segundo plano e fecha o terminal instantaneamente)
- **`Iniciar_Downloader.bat`** (Modo com terminal visível para depuração)

Ou via terminal Python:
```bash
python app.py
```

---

## 📦 Estrutura dos Arquivos

- **`bin/`**: Binários portáteis de alta performance:
  - `ffmpeg.exe` (v9.0.1 Full Build)
  - `ffprobe.exe`
  - `yt-dlp.exe`
- **`app.py`**: Interface gráfica moderna desenvolvida em PyQt6 Dark Theme.
- **`downloader_engine.py`**: Motor multithread gerenciador da fila, pré-busca assíncrona de títulos/miniaturas, extração de legendas e integração com FFmpeg.
- **`installer.iss`**: Script do Inno Setup para gerar o instalador executável oficial do Windows.
- **`Instalador_FFmpeg_Downloader.exe`**: Instalador final completo de 185 MB pronto para distribuição.
