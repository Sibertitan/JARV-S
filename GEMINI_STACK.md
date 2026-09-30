# Eklentileri Gemini altyapısında çalıştırma

Bu belge; **OmniRoute, Claude Mem, Headroom, Claude Code Setup ve Task Observer**
araçlarının hepsinin **Gemini** altyapısı üzerinden çalışmasını sağlar.

## Mimari (tek kilit nokta)

```
  Araç  ──►  OmniRoute (http://127.0.0.1:20128)  ──►  Gemini
```

OmniRoute `/v1` uç noktasını **hem OpenAI-uyumlu hem Anthropic-uyumlu** biçimde
sunar. Bu yüzden her aracın kendisini ayrı ayrı Gemini'ye "port" etmek gerekmez:
aracın model uç noktasını OmniRoute'a çevirmek yeter, OmniRoute isteği Gemini'ye
yönlendirir.

Listelenen 4 araç (Claude Code Setup, Claude Mem, Task Observer) **Claude Code'un
içinde** çalışır; dolayısıyla Claude Code'un uç noktasını OmniRoute'a çevirince
üçü birden Gemini'ye gider. Headroom ve OpenAI-uyumlu araçlar `OPENAI_BASE_URL`
ile aynı ağ geçidine bağlanır. JARVIS ise zaten yerleşik OmniRoute desteğiyle
`switch_brain omniroute` üzerinden Gemini'yi kullanır.

## Kurulum

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_gemini_stack.ps1 -OmniKey "<OmniRoute anahtarı>"
```

**Kali/Linux:**
```bash
./setup_gemini_stack.sh <OmniRoute anahtarı>
```

Betik şunları yapar:
1. OmniRoute çalışmıyorsa `work/omniroute-local` içinden başlatır.
2. `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` ortam değişkenlerini OmniRoute'a
   çevirir → Claude Code ve içindeki tüm eklenti/skill'ler Gemini'ye gider.
3. `OPENAI_BASE_URL` / `HEADROOM_BASE_URL` değişkenlerini OmniRoute'a çevirir →
   Headroom ve OpenAI-uyumlu araçlar Gemini'ye gider.

## Tek elle adım: Gemini anahtarını OmniRoute'a ekle

OmniRoute, kullanıcının **kendi** Gemini anahtarını kendi yerel veritabanında
saklar. Bir kez yapılır:

1. `http://127.0.0.1:20128/dashboard` → **Providers → Gemini**
2. `config/api_keys.json` içindeki `gemini_api_key` değerini oraya ekle.
3. **Endpoints** sekmesinden gerçek OmniRoute anahtarını kopyala ve kurulum
   betiğini o anahtarla bir kez daha çalıştır.

> Not: OmniRoute'un serbest (free-tier) Gemini-sınıfı sağlayıcıları anahtarsız da
> çalışabilir; kendi Gemini kotanı kullanmak istiyorsan yukarıdaki adım gerekir.

## Araç bazında durum

| Araç | Gemini'ye nasıl bağlanır | Durum |
|------|--------------------------|-------|
| **OmniRoute** | Ağ geçidinin kendisi; Gemini'ye yönlendirir | `work/omniroute-local`'da kurulu (3.8.51) |
| **JARVIS** | `omniroute_url` + `switch_brain omniroute` | `config/api_keys.json`'a bağlandı |
| **Claude Code Setup** | Claude Code → OmniRoute (ANTHROPIC_BASE_URL) | Betik ortamı ayarlar; `/plugin` ile kur |
| **Claude Mem** | Claude Code içinde → OmniRoute | Betik ortamı ayarlar; `npm i -g claude-mem` |
| **Task Observer** | Claude Code içinde → OmniRoute | Betik ortamı ayarlar; `/plugin` ile kur |
| **Headroom** | `HEADROOM_BASE_URL`/`OPENAI_BASE_URL` → OmniRoute | Betik ortamı ayarlar |

## Doğrulama

- `echo %ANTHROPIC_BASE_URL%` (Windows) / `echo $ANTHROPIC_BASE_URL` (Linux) →
  `http://127.0.0.1:20128` görünmeli.
- OmniRoute dashboard → **Analytics**: isteklerin Gemini sağlayıcısına düştüğünü
  ve `X-OmniRoute-Decision` başlığında Gemini'nin göründüğünü kontrol et.
