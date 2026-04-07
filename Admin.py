import tkinter as tk
from tkinter import filedialog, messagebox
import datetime
import os
import json
import shutil
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ImageTk

# ================= CONFIG =================

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "horarios.json")
IMG_DIR     = os.path.join(BASE_DIR, "imagens")
PORTA       = 8765          # porta do servidor HTTP — mude se necessário

os.makedirs(IMG_DIR, exist_ok=True)

CORES = {
    "fundo":        "#0D1117",
    "card":         "#161B22",
    "borda":        "#30363D",
    "destaque":     "#58A6FF",
    "texto":        "#E6EDF3",
    "texto_fraco":  "#8B949E",
    "verde":        "#3FB950",
    "vermelho":     "#F85149",
    "laranja":      "#F0883E",
    "input_fundo":  "#21262D",
    "btn_hover":    "#388BFD",
    "item_hover":   "#1C2128",
}

# ================= DADOS =================

def carregar_horarios():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def salvar_horarios(horarios):
    with open(CONFIG_FILE, "w") as f:
        json.dump(horarios, f, indent=4, ensure_ascii=False)

def validar_hora(s):
    try:
        datetime.datetime.strptime(s.strip(), "%H:%M")
        return True
    except ValueError:
        return False

def copiar_imagem_para_pasta(path_original):
    """Copia a imagem para a pasta /imagens local e retorna o novo caminho."""
    if not path_original or not os.path.exists(path_original):
        return ""
    nome = os.path.basename(path_original)
    destino = os.path.join(IMG_DIR, nome)
    if os.path.abspath(path_original) != os.path.abspath(destino):
        shutil.copy2(path_original, destino)
    return destino

def ip_local():
    """Descobre o IP da máquina na rede local."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ================= SERVIDOR HTTP =================

class Handler(BaseHTTPRequestHandler):
    """Servidor simples que serve o JSON e as imagens para o painel."""

    def log_message(self, format, *args):
        pass  # silencia logs no terminal

    def do_GET(self):
        # GET /horarios  → retorna o JSON
        if self.path == "/horarios":
            try:
                with open(CONFIG_FILE, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self.send_response(404)
                self.end_headers()

        # GET /imagem/<nome>  → retorna o arquivo de imagem
        elif self.path.startswith("/imagem/"):
            nome_arquivo = self.path[len("/imagem/"):]
            # segurança básica — sem ".." no caminho
            if ".." in nome_arquivo or "/" in nome_arquivo:
                self.send_response(403)
                self.end_headers()
                return
            caminho = os.path.join(IMG_DIR, nome_arquivo)
            if os.path.exists(caminho):
                ext = os.path.splitext(nome_arquivo)[1].lower()
                tipos = {".png": "image/png", ".jpg": "image/jpeg",
                         ".jpeg": "image/jpeg", ".bmp": "image/bmp",
                         ".gif": "image/gif", ".webp": "image/webp"}
                ct = tipos.get(ext, "application/octet-stream")
                with open(caminho, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


def iniciar_servidor(porta=PORTA):
    """Inicia o servidor HTTP em thread separada."""
    servidor = HTTPServer(("0.0.0.0", porta), Handler)
    t = threading.Thread(target=servidor.serve_forever, daemon=True)
    t.start()
    return servidor

# ================= WIDGETS AUXILIARES =================

def entry_dark(parent, placeholder="", **kw):
    e = tk.Entry(
        parent,
        bg=CORES["input_fundo"], fg=CORES["texto"],
        insertbackground=CORES["texto"],
        relief="flat", highlightthickness=1,
        highlightbackground=CORES["borda"],
        highlightcolor=CORES["destaque"],
        font=("Helvetica", 13), **kw
    )
    if placeholder:
        e.insert(0, placeholder)
        e.config(fg=CORES["texto_fraco"])
        def on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, "end")
                e.config(fg=CORES["texto"])
        def on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder)
                e.config(fg=CORES["texto_fraco"])
        e.bind("<FocusIn>",  on_focus_in)
        e.bind("<FocusOut>", on_focus_out)
    return e


def btn_dark(parent, texto, comando, cor_bg=None, cor_fg=None,
             cor_hover=None, largura=None, altura=32, fonte_size=12, bold=False):
    cor_bg    = cor_bg    or CORES["destaque"]
    cor_fg    = cor_fg    or "#FFFFFF"
    cor_hover = cor_hover or CORES["btn_hover"]
    peso      = "bold" if bold else "normal"
    b = tk.Button(
        parent, text=texto, command=comando,
        bg=cor_bg, fg=cor_fg,
        activebackground=cor_hover, activeforeground=cor_fg,
        relief="flat", cursor="hand2",
        font=("Helvetica", fonte_size, peso),
        bd=0, padx=12, pady=4,
    )
    if largura:
        b.config(width=largura)
    b.bind("<Enter>", lambda e: b.config(bg=cor_hover))
    b.bind("<Leave>", lambda e: b.config(bg=cor_bg))
    return b


def label(parent, texto, size=12, bold=False, cor=None, **kw):
    cor  = cor or CORES["texto"]
    peso = "bold" if bold else "normal"
    return tk.Label(parent, text=texto,
                    bg=CORES["card"], fg=cor,
                    font=("Helvetica", size, peso), **kw)

# ================= ADMIN =================

def iniciar_admin():
    horarios = carregar_horarios()
    imagem_selecionada = {"path": ""}

    # ── Inicia servidor HTTP
    ip  = ip_local()
    srv = iniciar_servidor(PORTA)

    root = tk.Tk()
    root.title("Administração de Horários — Alarme Escolar")
    root.geometry("880x680")
    root.minsize(700, 540)
    root.configure(bg=CORES["fundo"])

    # Barra topo
    tk.Frame(root, bg=CORES["destaque"], height=4).pack(fill="x", side="top")

    # ── Banner do servidor
    banner = tk.Frame(root, bg="#0F2027")
    banner.pack(fill="x", padx=0, pady=0)
    tk.Label(
        banner,
        text=f"Servidor ativo  X  Painel deve usar:  http://{ip}:{PORTA}",
        bg="#0F2027", fg=CORES["verde"],
        font=("Helvetica", 11, "bold"), anchor="w", padx=16, pady=6
    ).pack(side="left")

    # Botão copiar IP
    def copiar_ip():
        root.clipboard_clear()
        root.clipboard_append(f"http://{ip}:{PORTA}")
        root.update()
        btn_ip.config(text="Copiado", fg=CORES["verde"])
        root.after(2000, lambda: btn_ip.config(text="Copiar", fg=CORES["destaque"]))

    btn_ip = tk.Button(banner, text="Copiar", bg="#0F2027", fg=CORES["destaque"],
                       relief="flat", cursor="hand2",
                       font=("Helvetica", 11, "bold"),
                       command=copiar_ip, bd=0, padx=10)
    btn_ip.pack(side="right", padx=10)

    # ── Área principal
    area = tk.Frame(root, bg=CORES["fundo"])
    area.pack(fill="both", expand=True, padx=16, pady=12)
    area.columnconfigure(0, weight=2)
    area.columnconfigure(1, weight=3)
    area.rowconfigure(0, weight=1)

    # ============================================================
    # COLUNA ESQUERDA — lista de eventos
    # ============================================================
    col_esq = tk.Frame(area, bg=CORES["card"],
                       highlightthickness=1, highlightbackground=CORES["borda"])
    col_esq.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    col_esq.rowconfigure(1, weight=1)
    col_esq.columnconfigure(0, weight=1)

    cab_esq = tk.Frame(col_esq, bg=CORES["card"])
    cab_esq.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
    label(cab_esq, "Horários Cadastrados", size=13, bold=True).pack(side="left")
    lbl_qtd = label(cab_esq, "0 eventos", size=11, cor=CORES["texto_fraco"])
    lbl_qtd.pack(side="right")

    frame_scroll_outer = tk.Frame(col_esq, bg=CORES["card"])
    frame_scroll_outer.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 10))
    frame_scroll_outer.rowconfigure(0, weight=1)
    frame_scroll_outer.columnconfigure(0, weight=1)

    scroll_canvas = tk.Canvas(frame_scroll_outer, bg=CORES["fundo"], highlightthickness=0)
    scrollbar = tk.Scrollbar(frame_scroll_outer, orient="vertical", command=scroll_canvas.yview)
    scroll_canvas.configure(yscrollcommand=scrollbar.set)
    scroll_canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    frame_lista = tk.Frame(scroll_canvas, bg=CORES["fundo"])
    scroll_canvas.create_window((0, 0), window=frame_lista, anchor="nw")

    def _on_frame_configure(e):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
    frame_lista.bind("<Configure>", _on_frame_configure)

    # ============================================================
    # COLUNA DIREITA — formulário
    # ============================================================
    col_dir = tk.Frame(area, bg=CORES["card"],
                       highlightthickness=1, highlightbackground=CORES["borda"])
    col_dir.grid(row=0, column=1, sticky="nsew")
    col_dir.columnconfigure(0, weight=1)

    pad_x = 22

    label(col_dir, "Novo Evento", size=14, bold=True).grid(
        row=0, column=0, padx=pad_x, pady=(18, 2), sticky="w")

    label(col_dir, "Horário  (HH:MM)", size=11, cor=CORES["texto_fraco"]).grid(
        row=1, column=0, padx=pad_x, pady=(14, 2), sticky="w")
    entry_hora = entry_dark(col_dir, placeholder="Ex: 08:00")
    entry_hora.grid(row=2, column=0, padx=pad_x, pady=(0, 2), sticky="ew", ipady=7)
    lbl_err_hora = tk.Label(col_dir, text="", bg=CORES["card"],
                             fg=CORES["vermelho"], font=("Helvetica", 10))
    lbl_err_hora.grid(row=3, column=0, padx=pad_x, sticky="w")

    label(col_dir, "Nome do Evento", size=11, cor=CORES["texto_fraco"]).grid(
        row=4, column=0, padx=pad_x, pady=(10, 2), sticky="w")
    entry_nome = entry_dark(col_dir, placeholder="Ex: Recreio")
    entry_nome.grid(row=5, column=0, padx=pad_x, pady=(0, 2), sticky="ew", ipady=7)
    lbl_err_nome = tk.Label(col_dir, text="", bg=CORES["card"],
                             fg=CORES["vermelho"], font=("Helvetica", 10))
    lbl_err_nome.grid(row=6, column=0, padx=pad_x, sticky="w")

    label(col_dir, "Pictograma  (opcional)", size=11, cor=CORES["texto_fraco"]).grid(
        row=7, column=0, padx=pad_x, pady=(10, 2), sticky="w")

    frame_img_info = tk.Frame(col_dir, bg=CORES["input_fundo"],
                               highlightthickness=1, highlightbackground=CORES["borda"])
    frame_img_info.grid(row=8, column=0, padx=pad_x, pady=(0, 4), sticky="ew")
    frame_img_info.columnconfigure(0, weight=1)

    lbl_img_nome = tk.Label(frame_img_info, text="Nenhuma imagem selecionada",
                             bg=CORES["input_fundo"], fg=CORES["texto_fraco"],
                             font=("Helvetica", 11), anchor="w")
    lbl_img_nome.grid(row=0, column=0, padx=10, pady=6, sticky="ew")

    lbl_preview = tk.Label(frame_img_info, bg=CORES["input_fundo"], image="")

    def selecionar_imagem():
        path = filedialog.askopenfilename(
            title="Selecionar Pictograma",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")],
        )
        if path:
            imagem_selecionada["path"] = path
            nome = os.path.basename(path)
            lbl_img_nome.config(text=nome[:32] if len(nome) <= 32 else nome[:29]+"...",
                                fg=CORES["verde"])
            try:
                img  = Image.open(path).resize((72, 72), Image.LANCZOS)
                foto = ImageTk.PhotoImage(img)
                lbl_preview.config(image=foto)
                lbl_preview._foto = foto
                lbl_preview.grid(row=1, column=0, pady=(0, 8))
            except Exception:
                lbl_preview.grid_remove()
        else:
            imagem_selecionada["path"] = ""
            lbl_img_nome.config(text="Nenhuma imagem selecionada", fg=CORES["texto_fraco"])
            lbl_preview.grid_remove()

    btn_dark(col_dir, "Escolher imagem", selecionar_imagem,
             cor_bg=CORES["input_fundo"], cor_fg=CORES["destaque"],
             cor_hover=CORES["borda"], fonte_size=12).grid(
        row=9, column=0, padx=pad_x, pady=(2, 14), sticky="ew", ipady=4)

    tk.Frame(col_dir, bg=CORES["borda"], height=1).grid(
        row=10, column=0, padx=pad_x, pady=(0, 14), sticky="ew")

    btn_add = btn_dark(col_dir, "Adicionar Evento", lambda: None,
                       cor_bg=CORES["destaque"], bold=True, fonte_size=13)
    btn_add.grid(row=11, column=0, padx=pad_x, pady=(0, 20), sticky="ew", ipady=7)

    # ============================================================
    # FUNÇÕES
    # ============================================================

    def limpar_form():
        for e in (entry_hora, entry_nome):
            e.delete(0, "end")
            e.config(fg=CORES["texto_fraco"], highlightbackground=CORES["borda"])
        entry_hora.insert(0, "Ex: 08:00")
        entry_nome.insert(0, "Ex: Recreio")
        imagem_selecionada["path"] = ""
        lbl_img_nome.config(text="Nenhuma imagem selecionada", fg=CORES["texto_fraco"])
        lbl_preview.grid_remove()
        lbl_err_hora.config(text="")
        lbl_err_nome.config(text="")

    def atualizar_lista():
        for w in frame_lista.winfo_children():
            w.destroy()

        horarios_ord = sorted(horarios, key=lambda x: x.get("hora", ""))
        lbl_qtd.config(text=f"{len(horarios_ord)} evento{'s' if len(horarios_ord)!=1 else ''}")

        if not horarios_ord:
            tk.Label(frame_lista, text="Nenhum evento cadastrado.",
                     bg=CORES["fundo"], fg=CORES["texto_fraco"],
                     font=("Helvetica", 12)).pack(pady=24)
            return

        for item in horarios_ord:
            card = tk.Frame(frame_lista, bg=CORES["card"],
                            highlightthickness=1, highlightbackground=CORES["borda"])
            card.pack(fill="x", padx=4, pady=3)
            card.columnconfigure(1, weight=1)

            def _enter(e, c=card): c.config(bg=CORES["item_hover"])
            def _leave(e, c=card): c.config(bg=CORES["card"])
            card.bind("<Enter>", _enter)
            card.bind("<Leave>", _leave)

            tk.Label(card, text=item.get("hora","--:--"),
                     bg=CORES["card"], fg=CORES["destaque"],
                     font=("Helvetica", 17, "bold"), width=6).grid(
                row=0, column=0, padx=(10, 6), pady=10)

            tk.Label(card, text=item.get("nome","Evento"),
                     bg=CORES["card"], fg=CORES["texto"],
                     font=("Helvetica", 12), anchor="w").grid(
                row=0, column=1, sticky="ew")

            # mostra se tem imagem disponível na pasta local
            nome_img = os.path.basename(item.get("imagem",""))
            tem_img  = bool(nome_img and os.path.exists(os.path.join(IMG_DIR, nome_img)))
            tk.Label(card, text="[img]" if tem_img else "     ",
                     bg=CORES["card"], fg=CORES["texto_fraco"],
                     font=("Helvetica", 10)).grid(row=0, column=2, padx=6)

            idx = horarios.index(item)

            def _remover(i=idx):
                ev = horarios[i]
                if messagebox.askyesno(
                    "Confirmar remoção",
                    f"Remover '{ev.get('nome','')}' das {ev.get('hora','')}?"
                ):
                    horarios.pop(i)
                    salvar_horarios(horarios)
                    atualizar_lista()

            btn_dark(card, "X", _remover,
                     cor_bg=CORES["card"], cor_fg=CORES["texto_fraco"],
                     cor_hover=CORES["vermelho"], largura=3, fonte_size=13).grid(
                row=0, column=3, padx=(4, 8), pady=6)

    def adicionar():
        hora = entry_hora.get().strip()
        nome = entry_nome.get().strip()
        valido = True

        lbl_err_hora.config(text="")
        lbl_err_nome.config(text="")
        entry_hora.config(highlightbackground=CORES["borda"])
        entry_nome.config(highlightbackground=CORES["borda"])

        if hora in ("", "Ex: 08:00"):
            lbl_err_hora.config(text="Informe o horário")
            entry_hora.config(highlightbackground=CORES["vermelho"])
            valido = False
        elif not validar_hora(hora):
            lbl_err_hora.config(text="Use o formato HH:MM  (ex: 08:30)")
            entry_hora.config(highlightbackground=CORES["vermelho"])
            valido = False

        if nome in ("", "Ex: Recreio"):
            lbl_err_nome.config(text="Informe o nome do evento")
            entry_nome.config(highlightbackground=CORES["vermelho"])
            valido = False

        if not valido:
            return

        h, m   = map(int, hora.split(":"))
        hora_fmt = f"{h:02d}:{m:02d}"

        for ev in horarios:
            if ev["hora"] == hora_fmt:
                if not messagebox.askyesno(
                    "Horário duplicado",
                    f"Já existe um evento às {hora_fmt}.\nAdicionar mesmo assim?"
                ):
                    return

        # copia imagem para a pasta compartilhada
        path_img = copiar_imagem_para_pasta(imagem_selecionada["path"])
        nome_img = os.path.basename(path_img) if path_img else ""

        horarios.append({"hora": hora_fmt, "nome": nome, "imagem": nome_img})
        salvar_horarios(horarios)
        atualizar_lista()
        limpar_form()

        btn_add.config(text="Evento adicionado!", bg=CORES["verde"])
        root.after(2000, lambda: btn_add.config(
            text="Adicionar Evento", bg=CORES["destaque"]))

    btn_add.config(command=adicionar)
    entry_hora.bind("<Return>", lambda e: entry_nome.focus())
    entry_nome.bind("<Return>", lambda e: adicionar())

    atualizar_lista()
    root.mainloop()


if __name__ == "__main__":
    iniciar_admin()
