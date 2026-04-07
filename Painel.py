import tkinter as tk
import datetime
import os
import json
import subprocess
import threading
import urllib.request
from PIL import Image, ImageTk

# ================= CONFIG =================

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
IMG_DIR     = os.path.join(BASE_DIR, "imagens_cache")   # imagens baixadas do admin
SOM         = os.path.join(BASE_DIR, "sino.mp3")

# ──────────────────────────────────────────
#  ENDEREÇO DO ADMIN
#  Troque pelo IP que aparece na barra verde
#  do admin.py, por exemplo:
#       ADMIN_URL = "http://192.168.1.10:8765"
# ──────────────────────────────────────────
ADMIN_URL   = "http://10.61.5.40:8765"

SYNC_INTERVALO = 30   # segundos entre cada sincronização

os.makedirs(IMG_DIR, exist_ok=True)

CORES = {
    "fundo":       "#0D1117",
    "card":        "#161B22",
    "borda":       "#30363D",
    "destaque":    "#58A6FF",
    "texto":       "#E6EDF3",
    "texto_fraco": "#8B949E",
    "alerta":      "#FFD700",
    "verde":       "#3FB950",
    "vermelho":    "#F85149",
}

DIAS_PT  = ["Segunda-feira","Terça-feira","Quarta-feira",
            "Quinta-feira","Sexta-feira","Sábado","Domingo"]
MESES_PT = ["janeiro","fevereiro","março","abril","maio","junho",
            "julho","agosto","setembro","outubro","novembro","dezembro"]

# ================= SINCRONIZAÇÃO =================

horarios      = []
ultimo_sync   = {"ok": False, "ts": None}
_sync_lock    = threading.Lock()

def baixar_imagem(nome_arquivo):
    """Baixa uma imagem do admin se ainda não estiver em cache."""
    if not nome_arquivo:
        return
    destino = os.path.join(IMG_DIR, nome_arquivo)
    if os.path.exists(destino):
        return
    url = f"{ADMIN_URL}/imagem/{nome_arquivo}"
    try:
        urllib.request.urlretrieve(url, destino)
        print(f"[SYNC] Imagem baixada: {nome_arquivo}")
    except Exception as e:
        print(f"[SYNC] Erro ao baixar imagem '{nome_arquivo}': {e}")

def sincronizar():
    """Busca horarios.json do admin e baixa imagens novas. Roda em thread."""
    global horarios
    url = f"{ADMIN_URL}/horarios"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        with _sync_lock:
            horarios = dados
        ultimo_sync["ok"] = True
        ultimo_sync["ts"] = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[SYNC] Horários atualizados: {len(dados)} evento(s)")
        # baixa imagens que ainda não existem localmente
        for item in dados:
            baixar_imagem(item.get("imagem", ""))
    except Exception as e:
        ultimo_sync["ok"] = False
        print(f"[SYNC] Falha ao sincronizar: {e}")

def sync_loop(root, lbl_status):
    """Executa a sincronização periodicamente sem travar a UI."""
    def _fazer():
        sincronizar()
        # atualiza label de status na thread da UI
        root.after(0, _atualizar_status, lbl_status)
    threading.Thread(target=_fazer, daemon=True).start()
    root.after(SYNC_INTERVALO * 1000, sync_loop, root, lbl_status)

def _atualizar_status(lbl):
    if ultimo_sync["ok"]:
        lbl.config(text=f"🟢  Sincronizado às {ultimo_sync['ts']}",
                   fg=CORES["verde"])
    else:
        lbl.config(text="🔴  Sem conexão com o Admin — usando dados anteriores",
                   fg=CORES["vermelho"])

# ================= ÁUDIO =================

def tocar_sino():
    if not os.path.exists(SOM):
        print(f"[SINO] Arquivo não encontrado: {SOM}")
        return
    som_uri = f"file://{os.path.abspath(SOM)}"
    tentativas = [
        ["gst-launch-1.0", "playbin", f"uri={som_uri}"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", SOM],
        ["mpg123", "-q", SOM],
        ["aplay", SOM],
        ["paplay", SOM],
        ["cvlc", "--play-and-exit", SOM],
        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{SOM}').PlaySync()"],
        ["afplay", SOM],
    ]
    for cmd in tentativas:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[SINO] Tocando com: {cmd[0]}")
            return
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"[SINO] Erro com {cmd[0]}: {e}")
    print("[SINO] Nenhum player encontrado.")

# ================= UTILITÁRIOS =================

def agora_brasilia():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))

def criar_card(canvas, x, y, w, h, raio=20, cor_fundo=None, cor_borda=None):
    pontos = [
        x+raio, y,        x+w-raio, y,
        x+w,    y,        x+w,      y+raio,
        x+w,    y+h-raio, x+w,      y+h,
        x+w-raio, y+h,   x+raio,   y+h,
        x,      y+h,      x,        y+h-raio,
        x,      y+raio,   x,        y,
    ]
    return canvas.create_polygon(pontos, smooth=True,
                                 fill=cor_fundo or CORES["card"],
                                 outline=cor_borda or CORES["borda"], width=1)

def caminho_imagem_cache(nome_arquivo):
    """Retorna caminho local da imagem em cache, ou string vazia."""
    if not nome_arquivo:
        return ""
    p = os.path.join(IMG_DIR, nome_arquivo)
    return p if os.path.exists(p) else ""

# ================= ALERTA FULLSCREEN =================

def mostrar_alerta(root, item):
    janela = tk.Toplevel(root)
    janela.attributes("-fullscreen", True)
    janela.configure(bg="black")
    janela.lift()
    janela.focus_force()

    sw = janela.winfo_screenwidth()
    sh = janela.winfo_screenheight()

    canvas = tk.Canvas(janela, bg="black", highlightthickness=0)
    canvas.place(x=0, y=0, width=sw, height=sh)

    # usa imagem do cache local
    path_img = caminho_imagem_cache(item.get("imagem", ""))
    if path_img:
        try:
            img    = Image.open(path_img)
            iw, ih = img.size
            escala = max(sw / iw, sh / ih)
            novo_w = int(iw * escala)
            novo_h = int(ih * escala)
            img    = img.resize((novo_w, novo_h), Image.LANCZOS)
            left   = (novo_w - sw) // 2
            top    = (novo_h - sh) // 2
            img    = img.crop((left, top, left + sw, top + sh))
            foto   = ImageTk.PhotoImage(img)
            canvas.create_image(0, 0, image=foto, anchor="nw")
            canvas._foto = foto
        except Exception:
            pass

    # nome do evento sobre a imagem
    canvas.create_text(sw // 2, sh // 2,
                       text=item.get("nome", ""),
                       font=("Helvetica", int(sh * 0.08), "bold"),
                       fill="white",
                       anchor="center")

    janela.after(8000, janela.destroy)

# ================= PAINEL PRINCIPAL =================

def iniciar_painel():
    global horarios
    toques_hoje = set()

    root = tk.Tk()
    root.title("Painel Escolar")
    root.attributes("-fullscreen", True)
    root.configure(bg=CORES["fundo"])

    canvas = tk.Canvas(root, bg=CORES["fundo"], highlightthickness=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    canvas.create_rectangle(0, 0, 9999, 5, fill=CORES["destaque"], outline="")

    # ── barra de status (sincronização)
    barra_status = tk.Frame(root, bg="#0F2027")
    barra_status.place(relx=0, rely=1.0, relwidth=1, anchor="sw", height=30)

    lbl_status = tk.Label(
        barra_status,
        text="⏳  Conectando ao Admin…",
        bg="#0F2027", fg=CORES["texto_fraco"],
        font=("Helvetica", 10), anchor="w", padx=12
    )
    lbl_status.pack(side="left", fill="y")

    # botão forçar sincronização
    def forcar_sync():
        lbl_status.config(text="⏳  Sincronizando…", fg=CORES["texto_fraco"])
        threading.Thread(target=lambda: [
            sincronizar(),
            root.after(0, _atualizar_status, lbl_status)
        ], daemon=True).start()

    tk.Button(barra_status, text="Sincronizar agora",
              bg="#0F2027", fg=CORES["destaque"],
              relief="flat", cursor="hand2",
              font=("Helvetica", 10, "bold"),
              command=forcar_sync, bd=0, padx=10).pack(side="right", padx=8)

    # ── textos do painel
    id_hora   = canvas.create_text(0, 0, text="00:00:00",
                                   font=("Helvetica", 10, "bold"),
                                   fill=CORES["destaque"], anchor="center")
    id_data   = canvas.create_text(0, 0, text="",
                                   font=("Helvetica", 10),
                                   fill=CORES["texto_fraco"], anchor="center")
    id_titulo = canvas.create_text(0, 0, text="PRÓXIMO EVENTO",
                                   font=("Helvetica", 10, "bold"),
                                   fill=CORES["texto_fraco"], anchor="center")
    id_nome   = canvas.create_text(0, 0, text="Conectando…",
                                   font=("Helvetica", 10, "bold"),
                                   fill=CORES["texto"], anchor="center")
    id_tempo  = canvas.create_text(0, 0, text="",
                                   font=("Helvetica", 10),
                                   fill=CORES["destaque"], anchor="center")

    ids_card      = {"relogio": None, "evento": None}
    piscar_ativo  = [False]
    piscar_estado = [True]

    def piscar_loop():
        if not piscar_ativo[0]:
            return
        canvas.itemconfig(id_tempo, fill="#FF0000" if piscar_estado[0] else "#7A0000")
        piscar_estado[0] = not piscar_estado[0]
        root.after(400, piscar_loop)

    def redimensionar(event=None):
        w, h = root.winfo_width(), root.winfo_height()
        if w < 10 or h < 10:
            return
        cw = int(w * 0.70)
        cx = w // 2
        for cid in ids_card.values():
            if cid:
                canvas.delete(cid)
        ids_card["relogio"] = criar_card(canvas, cx - cw//2, int(h*0.04), cw, int(h*0.53))
        ids_card["evento"]  = criar_card(canvas, cx - cw//2, int(h*0.62), cw, int(h*0.26))
        for cid in ids_card.values():
            canvas.tag_lower(cid)
        canvas.coords(id_hora,   cx, int(h * 0.275))
        canvas.coords(id_data,   cx, int(h * 0.505))
        canvas.coords(id_titulo, cx, int(h * 0.668))
        canvas.coords(id_nome,   cx, int(h * 0.748))
        canvas.coords(id_tempo,  cx, int(h * 0.822))
        canvas.itemconfig(id_hora,   font=("Helvetica", max(10, int(h * 0.17)),  "bold"))
        canvas.itemconfig(id_data,   font=("Helvetica", max(10, int(h * 0.030))))
        canvas.itemconfig(id_titulo, font=("Helvetica", max(10, int(h * 0.022)), "bold"))
        canvas.itemconfig(id_nome,   font=("Helvetica", max(10, int(h * 0.050)), "bold"))
        canvas.itemconfig(id_tempo,  font=("Helvetica", max(10, int(h * 0.038)), "bold"))

    root.bind("<Configure>", redimensionar)

    def proximo_evento():
        agora   = agora_brasilia()
        futuros = []
        with _sync_lock:
            lista = list(horarios)
        for item in lista:
            try:
                h, m = map(int, item["hora"].split(":"))
                t = agora.replace(hour=h, minute=m, second=0, microsecond=0)
                if t >= agora:
                    futuros.append((t, item))
            except Exception:
                continue
        return min(futuros, key=lambda x: x[0]) if futuros else None

    def atualizar():
        agora    = agora_brasilia()
        hora_str = agora.strftime("%H:%M")

        canvas.itemconfig(id_hora, text=agora.strftime("%H:%M:%S"))
        canvas.itemconfig(id_data,
            text=f"{DIAS_PT[agora.weekday()]}, {agora.day} de "
                 f"{MESES_PT[agora.month-1]} de {agora.year}")

        prox = proximo_evento()
        if prox:
            horario, item = prox
            total_s     = int((horario - agora).total_seconds())
            texto_tempo = f"{item['hora']} — Faltam {total_s//60:02d}:{total_s%60:02d}"
            canvas.itemconfig(id_nome,  text=item.get("nome", "Evento"))
            canvas.itemconfig(id_tempo, text=texto_tempo)
            if total_s < 60:
                if not piscar_ativo[0]:
                    piscar_ativo[0] = True
                    piscar_loop()
            else:
                if piscar_ativo[0]:
                    piscar_ativo[0] = False
                if total_s < 300:
                    canvas.itemconfig(id_tempo, fill=CORES["alerta"])
                elif total_s > 900:
                    canvas.itemconfig(id_tempo, fill=CORES["destaque"])
        else:
            piscar_ativo[0] = False
            msg = "Sem eventos hoje" if horarios else "Aguardando dados do Admin…"
            canvas.itemconfig(id_nome,  text=msg)
            canvas.itemconfig(id_tempo, text="", fill=CORES["texto_fraco"])

        # disparo do sino
        if hora_str not in toques_hoje:
            with _sync_lock:
                lista = list(horarios)
            for item in lista:
                if item["hora"] == hora_str:
                    tocar_sino()
                    mostrar_alerta(root, item)
                    toques_hoje.add(hora_str)

        root.after(1000, atualizar)

    root.after(150, redimensionar)

    # primeira sincronização logo ao iniciar
    threading.Thread(target=lambda: [
        sincronizar(),
        root.after(0, _atualizar_status, lbl_status)
    ], daemon=True).start()

    # loop de sincronização periódica
    root.after(SYNC_INTERVALO * 1000, sync_loop, root, lbl_status)

    atualizar()
    root.mainloop()


if __name__ == "__main__":
    iniciar_painel()
