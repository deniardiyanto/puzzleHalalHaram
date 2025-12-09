import kivy
kivy.require("2.3.0")

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, NumericProperty
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle
from kivy.clock import Clock
from kivy.animation import Animation
from random import randint, choice
import os
import json

# ----------------------------
# Draggable Bubble
# ----------------------------
class DraggableBubble(ButtonBehavior, FloatLayout):
    is_dragging = BooleanProperty(False)
    original_pos = ListProperty([0, 0])
    label_text = ObjectProperty(None)

    def __init__(self, text, bg_color, dx=1, dy=2, **kwargs):
        super().__init__(**kwargs)

        # bubble size behavior
        self.size_hint = (None, None)
        self.min_width = 150      # minimum width
        self.max_width = 380      # maximum width before wrap
        self.height = 80          # default height

        self.dx = dx
        self.dy = dy
        self.bg_color = bg_color

        # background ellipse
        with self.canvas.before:
            Color(*self.bg_color)
            self.bg_rect = Ellipse(pos=self.pos, size=self.size)

        # text label
        self.label_text = Label(
            text=text,
            font_size="26sp",
            color=(1, 1, 1, 1),
            bold=True,
            halign="center",
            valign="middle",
            padding=(20, 10),
            size_hint=(None, None),
        )
        self.label_text.bind(texture_size=self.adjust_size_from_text)
        self.add_widget(self.label_text)

        # listeners
        self.bind(pos=self.update_graphics)
        self.bind(size=self.update_graphics)
        self.bind(size=self.update_label_wrap)

        # auto movement
        Clock.schedule_interval(self.auto_move, 1/60)

    # adjust size according to text
    def adjust_size_from_text(self, *args):
        lw, lh = self.label_text.texture_size
        new_width = lw + 40   # extra for padding
        new_height = lh + 20

        # apply limits
        new_width = max(self.min_width, min(new_width, self.max_width))

        self.size = (new_width, new_height)

    # update wrapping when width changes
    def update_label_wrap(self, *args):
        self.label_text.text_size = (self.width - 40, None)  # wrap text inside bubble

    # update graphics pos
    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

        self.label_text.pos = (
            self.x + (self.width - self.label_text.width) / 2,
            self.y + (self.height - self.label_text.height) / 2
        )

    # bubble auto movement
    def auto_move(self, dt):
        if self.is_dragging or not self.parent:
            return

        # check pause flag on parent screen
        p = self.parent
        paused = False
        # also try to find bucket tops from ancestor
        buckets_top = 0
        while p is not None:
            if hasattr(p, "is_paused"):
                paused = getattr(p, "is_paused")
                # try to obtain buckets if available on the GameScreen
                try:
                    if hasattr(p, "bucket_halal") and hasattr(p, "bucket_haram"):
                        try:
                            halal_top = p.bucket_halal.top
                            haram_top = p.bucket_haram.top
                            buckets_top = max(halal_top, haram_top)
                        except Exception:
                            buckets_top = 0
                except Exception:
                    buckets_top = 0
                break
            p = getattr(p, "parent", None)
        if paused:
            return

        # move
        self.x += self.dx
        self.y += self.dy

        # safe parent bounds
        try:
            pw = self.parent.width
            ph = self.parent.height
        except Exception:
            pw = 800
            ph = 600

        # horizontal bounce
        if self.x < 10:
            self.x = 10
            self.dx *= -1
        if self.right > pw - 10:
            self.x = pw - 10 - self.width
            self.dx *= -1

        # vertical constraints: do not go into bucket area
        min_allowed_y = buckets_top + 8  # sedikit jarak dari bucket top
        # also keep some minimum screen area (avoid too low)
        min_allowed_y = max(min_allowed_y, ph * 0.28)

        if self.y < min_allowed_y:
            # push the bubble back above the buckets
            self.y = min_allowed_y
            # make sure it moves upward
            if self.dy <= 0:
                self.dy = abs(self.dy) if self.dy != 0 else (2 + getattr(self, "level", 0))
        if self.top > ph - 20:
            # bounce at top
            self.y = ph - 20 - self.height
            if self.dy >= 0:
                self.dy *= -1

    # drag handlers
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.is_dragging = True
            self.original_pos = self.pos[:]
            # bring to front
            if self.parent:
                try:
                    children = self.parent.children[:]
                    if children and children[0] != self:
                        children.remove(self)
                        children.insert(0, self)
                        self.parent.children[:] = children
                except Exception:
                    pass
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.is_dragging:
            self.x = touch.x - self.width / 2
            self.y = touch.y - self.height / 2
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.is_dragging:
            self.is_dragging = False
            return True
        return super().on_touch_up(touch)



# ----------------------------
# Drop Bucket
# ----------------------------
class DropBucket(BoxLayout):
    def __init__(self, label, color, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = 150
        self.padding = 10
        self.spacing = 5
        with self.canvas.before:
            Color(*color)
            self.bg_rect = RoundedRectangle(radius=[30], pos=self.pos, size=self.size)
        self.text = Label(text=label, font_size="22sp", color=(1,1,1,1), bold=True)
        self.add_widget(self.text)
        self.bind(pos=self.update_graphics)
        self.bind(size=self.update_graphics)

    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


# ----------------------------
# Game Screen
# ----------------------------
class GameScreen(Screen):
    lives = NumericProperty(6)
    score = NumericProperty(0)
    level = NumericProperty(1)
    is_paused = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # main float layout for screen
        self.root_layer = FloatLayout()
        self.add_widget(self.root_layer)

        # background
        with self.root_layer.canvas:
            Color(0.92, 0.96, 1, 1)
            self.bg_rect = Rectangle(pos=self.root_layer.pos, size=self.root_layer.size)
        self.root_layer.bind(size=self.update_bg, pos=self.update_bg)

        # hearts box
        self.hearts_box = BoxLayout(orientation="horizontal", spacing=8, size_hint=(None,None),
                                    pos_hint={"x":0.02,"y":0.88})
        self.hearts_box.height = 44
        self.root_layer.add_widget(self.hearts_box)

        self.heart_images = []
        heart_path = os.path.join("assets","icons","heart.png")
        if os.path.exists(heart_path):
            for i in range(6):
                img = Image(source=heart_path, size_hint=(None,None), size=(44,44))
                self.heart_images.append(img)
                self.hearts_box.add_widget(img)
        else:
            fallback = Label(text="♥♥♥", font_size="28sp", color=(1,0,0,1))
            self.hearts_box.add_widget(fallback)
            self.heart_images = None

        # score label
        self.score_label = Label(text=f"Score: {self.score}", font_size="24sp", bold=True,
                                 size_hint=(None,None), size=(200,50),
                                 pos_hint={"right":0.98,"top":0.95}, color=(0.2,0.6,0.9,1))
        self.root_layer.add_widget(self.score_label)

        # pause button (text icon) with circular bg drawn
        self.pause_btn = Button(
            size_hint=(None,None),
            size=(90,90),
            pos_hint={"right": 0.98, "top": 0.80},
            background_normal="assets/icons/pause_icon2.png",
            background_down="assets/icons/pause_icon2.png",
            font_size="28sp"
        )
        # position it on screen using pos_hint by adding to root_layer and setting pos manually on resize
        self.root_layer.add_widget(self.pause_btn)
        # draw circle behind the button
        with self.pause_btn.canvas.before:
            Color(0,0,0,0)
            self.pause_circle = Ellipse(pos=self.pause_btn.pos, size=self.pause_btn.size)
        # Stop touch agar pause tidak mengurangi nyawa
        # ensure the circle follows the button
        def _update_circle(instance, *l):
            try:
                self.pause_circle.pos = instance.pos
                self.pause_circle.size = instance.size
            except Exception:
                pass
        self.pause_btn.bind(pos=_update_circle, size=_update_circle)

        # place pause button top-right on layout resize
        def _place_pause(*a):
            rw, rh = self.root_layer.width, self.root_layer.height
            # align at 4% margin
            margin_x = max(12, rw * 0.02)
            margin_y = max(12, rh * 0.02)
            self.pause_btn.pos = (rw - self.pause_btn.width - margin_x, rh - self.pause_btn.height - margin_y)
        self.root_layer.bind(size=_place_pause, pos=_place_pause)
        # bind action
        self.pause_btn.bind(on_release=lambda x: self.pause_game())

        # buckets bottom
        bucket_area = BoxLayout(orientation="horizontal", size_hint=(1,0.25),
                                pos_hint={"x":0,"y":0}, padding=20, spacing=20)
        self.root_layer.add_widget(bucket_area)
        self.bucket_halal = DropBucket("HALAL",(0.2,0.8,0.4,1))
        self.bucket_haram = DropBucket("HARAM",(0.85,0.25,0.3,1))
        bucket_area.add_widget(self.bucket_halal)
        bucket_area.add_widget(self.bucket_haram)

        # bubble storage
        self.bubble_widgets = []

        # sounds
        self.bgm = None
        try:
            self.bgm = SoundLoader.load("assets/sounds/bgm_piano_islamic.wav")
            if self.bgm:
                self.bgm.loop = True
                self.bgm.volume = 0.4
                self.bgm.play()
        except Exception:
            self.bgm = None

        try:
            self.correct_sfx = SoundLoader.load("assets/sounds/correct.wav")
            self.wrong_sfx = SoundLoader.load("assets/sounds/wrong.wav")
        except Exception:
            self.correct_sfx = None
            self.wrong_sfx = None

        # initial spawn
        Clock.schedule_once(lambda dt: self.spawn_bubble_step(), 0)
        self.update_lives_display()

        # pause overlay holder
        self.pause_layer = None
        # load foods dataset from json
        self.food_dataset = []
        json_path = os.path.join("assets", "datasets", "food.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # convert status Halal / Haram → matching text for bucket
                for item in data:
                    name = item.get("name", "")
                    status = item.get("status", "").upper()
                    notes = item.get("notes", "")
                    if status in ("HALAL", "HARAM"):
                        self.food_dataset.append((name, status, notes))
        except Exception as e:
            print("Failed loading foods JSON:", e)


    def update_bg(self, *args):
        try:
            self.bg_rect.pos = self.root_layer.pos
            self.bg_rect.size = self.root_layer.size
        except Exception:
            pass

    # ----------------------------
    # spawn bubble (respects is_paused)
    # ----------------------------
    def spawn_bubble_step(self):
        if self.is_paused:
            # retry after short delay to resume spawning when unpaused
            Clock.schedule_once(lambda dt: self.spawn_bubble_step(), 0.5)
            return

        if not self.food_dataset:  # jika json gagal
            return

        # ambil acak dari JSON
        name, status, notes = choice(self.food_dataset)
        # item = choice(self.food_dataset)
        # name = item["name"]
        # status = item["status"]
        # notes = item.get("notes", "")

        colors = [
            (0.2,0.6,1,1),(1,0.5,0.6,1),(0.7,0.4,1,1),
            (1,0.65,0.25,1),(0.25,0.8,0.7,1)
        ]

        bubble_height = 80
        margin = 12

        # compute bucket top y (safely)
        try:
            halal_top = self.bucket_halal.top
            haram_top = self.bucket_haram.top
            buckets_top = max(halal_top, haram_top)
        except Exception:
            buckets_top = 0

        # ensure start_y is above the buckets (buckets_top + margin)
        try:
            # prefer spawning somewhat above hearts or above buckets, whichever is higher
            hearts_y = max(0, getattr(self.hearts_box, "y", 0))
            default_start = max(hearts_y - bubble_height - margin, buckets_top + margin + 10)
            # but don't spawn below a sensible minimum
            start_y = max(default_start, buckets_top + margin + 10)
        except Exception:
            start_y = max(150, buckets_top + margin + 10)

        color = choice(colors)
        try:
            start_x = randint(50, int(self.root_layer.width * 0.75))
        except Exception:
            start_x = randint(50, 300)

        dx = choice([-2, -1, 1, 2]) + self.level
        dy = choice([2,3,4]) + self.level
        b = DraggableBubble(text=name, bg_color=color, dx=dx, dy=dy, pos=(start_x, start_y))
        b.category = status
        b.notes = notes
        self.root_layer.add_widget(b)
        self.bubble_widgets.append(b)

        interval = max(0.5, 3 - self.level * 0.2)
        Clock.schedule_once(lambda dt: self.spawn_bubble_step(), interval)

    # ----------------------------
    # drop check
    # ----------------------------
    def on_touch_up(self, touch):
        result = super().on_touch_up(touch)
        for w in list(self.root_layer.children):
            if isinstance(w, DraggableBubble) and not w.is_dragging:
                if self.check_drop(w):
                    return True
        return result

    def check_drop(self, b):
        if b.collide_widget(self.bucket_halal):
            if b.category == "HALAL":
                self.correct(b)
            else:
                self.wrong(b)
            return True
        if b.collide_widget(self.bucket_haram):
            if b.category == "HARAM":
                self.correct(b)
            else:
                self.wrong(b)
            return True
        return False
        
    def show_education_popup(self, bubble):
        self.is_paused = True

        overlay = FloatLayout(size_hint=(1,1))
        with overlay.canvas:
            Color(0, 0, 0, 0.55)
            overlay.dim_rect = Rectangle(pos=self.root_layer.pos, size=self.root_layer.size)

        card = BoxLayout(orientation="vertical", spacing=14, padding=22,
                         size_hint=(None, None), size=(480, 380),
                         pos_hint={"center_x":0.5,"center_y":0.5})
        with card.canvas.before:
            Color(1, 1, 1, 1)
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[22])
        card.bind(pos=lambda *a: setattr(card.bg, 'pos', card.pos),
                  size=lambda *a: setattr(card.bg, 'size', card.size))

        title = Label(text=f"[b]{bubble.label_text.text}[/b]", markup=True,
                      font_size="32sp", color=(0,0,0,1))
        card.add_widget(title)

        info = Label(text=bubble.notes, font_size="22sp", halign="center",
                     valign="middle", color=(0,0,0,1), text_size=(420, None))
        card.add_widget(info)

        btn_ok = Button(text="Lanjut", size_hint=(1, None), height=70,
                        background_normal="", background_color=(0.1, 0.65, 0.28, 1),
                        font_size="24sp", color=(1,1,1,1))
        card.add_widget(btn_ok)

        overlay.add_widget(card)
        self.add_widget(overlay)

        def close_popup(*a):
            self.remove_widget(overlay)
            self.is_paused = False
            # baru hapus bubble setelah popup ditutup
            self.safe_remove_widget(bubble)

        btn_ok.bind(on_release=close_popup)

        # animasi popup agar lebih hidup
        card.opacity = 0
        card.scale = 0.6
        Animation(opacity=1, duration=0.28, t="out_cubic").start(card)
        Animation(scale=1, duration=0.28, t="out_cubic").start(card)



    # ----------------------------
    # correct / wrong
    # ----------------------------
    def correct(self, bubble):
        try:
            if self.correct_sfx:
                self.correct_sfx.play()
        except Exception:
            pass
        anim = Animation(opacity=0, duration=0.25)
        anim.bind(on_complete=lambda *args: self.safe_remove_widget(bubble))
        anim.start(bubble)
        self.score += 10
        self.score_label.text = f"Score: {self.score}"
        self.level = max(1, self.score // 50 + 1)
         # popup edukasi
        self.show_education_popup(bubble)

    def wrong(self, bubble):
        try:
            if self.wrong_sfx:
                self.wrong_sfx.play()
        except Exception:
            pass
        bubble.pos = bubble.original_pos
        self.lives -= 1
        self.update_lives_display()
        if self.lives <= 0:
            self.game_over_popup()

    def safe_remove_widget(self, w):
        try:
            if w in self.root_layer.children:
                self.root_layer.remove_widget(w)
        except Exception:
            pass
        try:
            if w in self.bubble_widgets:
                self.bubble_widgets.remove(w)
        except Exception:
            pass

    # ----------------------------
    # lives display
    # ----------------------------
    def update_lives_display(self):
        if self.heart_images is None:
            try:
                lbl = self.hearts_box.children[0]
                lbl.text = "♥" * max(0, self.lives)
            except Exception:
                pass
        else:
            for i, img in enumerate(self.heart_images):
                img.opacity = 1.0 if i < self.lives else 0.25

    # ----------------------------
    # pause menu (overlay)
    # ----------------------------
    def pause_game(self):
        if self.is_paused:
            return
        self.is_paused = True

        # stop bubbles (backup dx/dy)
        for b in self.bubble_widgets:
            try:
                b.dx_backup = b.dx
                b.dy_backup = b.dy
                b.dx = 0
                b.dy = 0
            except Exception:
                pass

        # soften BGM
        if self.bgm:
            try:
                self.bgm_volume_before_pause = self.bgm.volume
                self.bgm.volume = 0.08
            except Exception:
                pass

        # create overlay
        overlay = FloatLayout(size_hint=(1,1))
        # dim background
        with overlay.canvas:
            Color(0, 0, 0, 0.55)
            overlay.dim_rect = Rectangle(pos=self.root_layer.pos, size=self.root_layer.size)

        # card
        card = BoxLayout(orientation="vertical", spacing=14, padding=22,
                         size_hint=(None, None), size=(360, 360), pos_hint={"center_x":0.5, "center_y":0.5})
        with card.canvas.before:
            Color(0.08, 0.08, 0.08, 0.98)
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[20])
        def _upd_card(*a):
            card.bg.pos = card.pos
            card.bg.size = card.size
        card.bind(pos=_upd_card, size=_upd_card)

        # title
        title = Label(text="[b]PAUSED[/b]", markup=True, font_size="30sp", size_hint=(1, None), height=60, color=(1,1,1,1))
        card.add_widget(title)

        # button factory
        def big_btn(txt, color):
            return Button(text=txt, size_hint=(1, None), height=64, font_size="20sp",
                          background_normal="", background_color=color, color=(1,1,1,1))
        btn_resume = big_btn("Resume", (0.22,0.7,0.36,1))
        btn_restart = big_btn("Restart", (0.12,0.56,1,1))
        btn_menu = big_btn("Main Menu", (0.9,0.25,0.3,1))

        card.add_widget(btn_resume)
        card.add_widget(btn_restart)
        card.add_widget(btn_menu)

        overlay.add_widget(card)
        self.pause_layer = overlay
        self.add_widget(overlay)

        # actions
        btn_resume.bind(on_release=lambda x: self._resume_from_overlay())
        btn_restart.bind(on_release=lambda x: self._restart_from_overlay())
        btn_menu.bind(on_release=lambda x: self._menu_from_overlay())

    def _resume_from_overlay(self):
        # remove overlay
        try:
            if self.pause_layer:
                self.remove_widget(self.pause_layer)
                self.pause_layer = None
        except Exception:
            pass
        # restore movement
        for b in self.bubble_widgets:
            if hasattr(b, "dx_backup"):
                b.dx = b.dx_backup
            if hasattr(b, "dy_backup"):
                b.dy = b.dy_backup
        # restore bgm
        if self.bgm:
            try:
                self.bgm.volume = getattr(self, "bgm_volume_before_pause", 0.4)
            except Exception:
                pass
        self.is_paused = False

    def _restart_from_overlay(self):
        # remove overlay
        try:
            if self.pause_layer:
                self.remove_widget(self.pause_layer)
                self.pause_layer = None
        except Exception:
            pass
        # restart
        self._do_restart()

    def _menu_from_overlay(self):
        try:
            if self.pause_layer:
                self.remove_widget(self.pause_layer)
                self.pause_layer = None
        except Exception:
            pass
        # stop bgm
        try:
            if self.bgm:
                self.bgm.stop()
        except Exception:
            pass
        self.is_paused = False
        # switch to menu
        try:
            self.manager.current = "menu"
        except Exception:
            pass

    # compatibility: previous resume_game name
    def resume_game(self):
        self._resume_from_overlay()

    # ----------------------------
    # game over (keeps popup)
    # ----------------------------
    def game_over_popup(self):
        if self.is_paused:
            return
        self.is_paused = True

        # stop bubble movement
        for b in self.bubble_widgets:
            try:
                b.dx = 0
                b.dy = 0
            except Exception:
                pass

        # soften BGM
        if hasattr(self, "bgm") and self.bgm:
            try:
                self.bgm_volume_before_pause = self.bgm.volume
                self.bgm.volume = 0.05
            except Exception:
                pass

        # create overlay like pause
        overlay = FloatLayout(size_hint=(1,1))
        with overlay.canvas:
            Color(0, 0, 0, 0.55)
            overlay.dim_rect = Rectangle(pos=self.root_layer.pos, size=self.root_layer.size)

        # card
        card = BoxLayout(orientation="vertical", spacing=14, padding=22,
                         size_hint=(None, None), size=(360, 270),
                         pos_hint={"center_x":0.5, "center_y":0.5})

        with card.canvas.before:
            Color(0.10, 0.08, 0.08, 0.97)
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[20])
        def _upd_card(*a):
            card.bg.pos = card.pos
            card.bg.size = card.size
        card.bind(pos=_upd_card, size=_upd_card)

        # title
        title = Label(text="[b]GAME OVER[/b]", markup=True,
                      font_size="32sp", size_hint=(1, None), height=60, color=(1,1,1,1))
        card.add_widget(title)

        # button factory
        def big_btn(txt, color):
            return Button(text=txt, size_hint=(1, None), height=64, font_size="20sp",
                          background_normal="", background_color=color, color=(1,1,1,1))

        btn_retry = big_btn("Retry",    (0.12, 0.56, 1, 1))
        btn_menu  = big_btn("Main Menu", (0.9, 0.25, 0.3, 1))

        card.add_widget(btn_retry)
        card.add_widget(btn_menu)

        overlay.add_widget(card)
        self.pause_layer = overlay   # supaya bisa dihapus nanti
        self.add_widget(overlay)

        # actions
        btn_retry.bind(on_release=lambda x: self._restart_from_overlay())
        btn_menu.bind(on_release=lambda x: self._menu_from_overlay())


    def _do_restart(self):
        # reset state
        self.lives = 6
        self.score = 0
        self.level = 1
        try:
            self.score_label.text = f"Score: {self.score}"
        except Exception:
            pass
        self.update_lives_display()
        self.clear_bubbles()
        # restart bgm
        try:
            if self.bgm:
                self.bgm.stop()
                self.bgm.play()
                self.bgm.volume = 0.4
        except Exception:
            pass
        self.is_paused = False
        Clock.schedule_once(lambda dt: self.spawn_bubble_step(), 0)

    def reset_game(self, popup):
        try:
            popup.dismiss()
        except Exception:
            pass
        self._do_restart()

    def clear_bubbles(self):
        for c in list(self.root_layer.children):
            if isinstance(c, DraggableBubble):
                try:
                    self.root_layer.remove_widget(c)
                except Exception:
                    pass
        self.bubble_widgets = []

    def back_to_menu_popup(self):
        # stop bgm safely then go to menu
        try:
            if self.bgm:
                self.bgm.stop()
        except Exception:
            pass
        try:
            self.manager.current = "menu"
        except Exception:
            pass


# ----------------------------
# Main Menu Screen
# ----------------------------
class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        title = Label(text="PuHaRam", font_size="36sp", bold=True,
                      pos_hint={"center_x":0.5,"center_y":0.7}, color=(0.08,0.4,0.6,1))
        layout.add_widget(title)

        start_btn = Button(text="Start Game", size_hint=(0.5, 0.14), pos_hint={"center_x":0.5,"center_y":0.48},
                           font_size="22sp", background_color=(0.16,0.56,1,1), color=(1,1,1,1))
        layout.add_widget(start_btn)
        start_btn.bind(on_release=lambda x: self.start_game())

        # Add Exit Button
        exit_btn = Button(text="Exit", size_hint=(0.5, 0.14), pos_hint={"center_x":0.5,"center_y":0.32},
                          font_size="22sp", background_color=(1,0.25,0.25,1), color=(1,1,1,1))
        layout.add_widget(exit_btn)
        exit_btn.bind(on_release=lambda x: App.get_running_app().stop())


        # small info at bottom
        info = Label(text="Tap the bubble and drag to correct bucket", font_size="14sp",
                     pos_hint={"center_x":0.5,"center_y":0.18}, color=(0.2,0.2,0.2,1))
        layout.add_widget(info)

        self.add_widget(layout)

    def start_game(self):
        self.manager.current = "game"


# ----------------------------
# App
# ----------------------------
class PuHaRam(App):
    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(MainMenuScreen(name="menu"))
        sm.add_widget(GameScreen(name="game"))
        sm.current = "menu"
        return sm

if __name__ == "__main__":
    PuHaRam().run()
