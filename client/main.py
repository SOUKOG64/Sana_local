"""Kivy-клиент «Арт-Фехтование». Данные хранятся локально на устройстве (SQLite), сервер не нужен."""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager

from api import ApiClient, ApiError

WEAPONS = ["рапира", "сабля", "шпага", "меч", "кинжал"]


class LoginScreen(Screen):
    def on_pre_enter(self, *args):
        self.ids.password.text = ""

    def do_login(self):
        app = App.get_running_app()
        email, password = self.ids.email.text.strip(), self.ids.password.text
        if not email or not password:
            return app.notify("Введите email и пароль", error=True)
        try:
            app.api.login(email, password)
        except ApiError as e:
            return app.handle_error(e)
        app.notify("Вход выполнен")
        app.go("home")


class RegisterScreen(Screen):
    def do_register(self):
        app = App.get_running_app()
        email, p1, p2 = self.ids.email.text.strip(), self.ids.password.text, self.ids.password2.text
        if not email or not p1:
            return app.notify("Заполните все поля", error=True)
        if p1 != p2:
            return app.notify("Пароли не совпадают", error=True)
        try:
            app.api.register(email, p1)
        except ApiError as e:
            return app.handle_error(e)
        app.notify("Аккаунт создан")
        app.go("home")


class HomeScreen(Screen):
    def on_pre_enter(self, *args):
        app = App.get_running_app()
        self.ids.hello.text = f"Вы вошли как {app.api.email}"
        try:
            self.ids.stats.text = f"Фехтовальщиков в базе: {len(app.api.list_fighters())}"
        except ApiError as e:
            self.ids.stats.text = ""
            app.handle_error(e)


class ListScreen(Screen):
    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        weapon = self.ids.weapon.text
        try:
            items = app.api.list_fighters(self.ids.search.text.strip(),
                                          None if weapon == "Все" else weapon)
        except ApiError as e:
            return app.handle_error(e)
        box = self.ids.box
        box.clear_widgets()
        if not items:
            box.add_widget(Label(text="Ничего не найдено", size_hint_y=None, height=dp(48)))
        for f in items:
            btn = Button(
                text=f"{f['full_name']}\n{f['weapon']} · {f['club'] or 'без клуба'} · рейтинг {f['rating']}",
                size_hint_y=None, height=dp(64), halign="left", valign="middle",
                background_normal="", background_color=(0.18, 0.18, 0.24, 1),
            )
            btn.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(24), s[1])))
            btn.bind(on_release=lambda _w, fid=f["id"]: app.open_detail(fid))
            box.add_widget(btn)


class DetailScreen(Screen):
    fighter_id = None

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        try:
            f = app.api.get_fighter(self.fighter_id)
        except ApiError as e:
            app.handle_error(e)
            return app.go("list")
        self.ids.name.text = f["full_name"]
        self.ids.info.text = (
            f"Оружие: [b]{f['weapon']}[/b]\n"
            f"Клуб: [b]{f['club'] or '—'}[/b]\n"
            f"Опыт: [b]{f['experience_years']}[/b] лет\n"
            f"Рейтинг: [b]{f['rating']}[/b]\n\n"
            f"{f['bio'] or ''}"
        )


class FormScreen(Screen):
    fighter_id = None  # None — создание, число — редактирование

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        ids = self.ids
        if self.fighter_id is None:
            ids.title.text = "Новый фехтовальщик"
            ids.full_name.text = ids.club.text = ids.bio.text = ""
            ids.experience.text = ids.rating.text = "0"
            ids.weapon.text = WEAPONS[0]
            return
        try:
            f = app.api.get_fighter(self.fighter_id)
        except ApiError as e:
            app.handle_error(e)
            return app.go("list")
        ids.title.text = "Редактирование"
        ids.full_name.text = f["full_name"]
        ids.weapon.text = f["weapon"]
        ids.club.text = f["club"] or ""
        ids.experience.text = str(f["experience_years"])
        ids.rating.text = str(f["rating"])
        ids.bio.text = f["bio"] or ""

    def save(self):
        app = App.get_running_app()
        ids = self.ids
        if len(ids.full_name.text.strip()) < 2:
            return app.notify("Введите ФИО (минимум 2 символа)", error=True)
        data = {
            "full_name": ids.full_name.text.strip(),
            "weapon": ids.weapon.text,
            "club": ids.club.text.strip() or None,
            "experience_years": ids.experience.text.strip(),
            "rating": ids.rating.text.strip(),
            "bio": ids.bio.text.strip() or None,
        }
        try:
            if self.fighter_id is None:
                app.api.create_fighter(data)
            else:
                app.api.update_fighter(self.fighter_id, data)
        except ApiError as e:
            return app.handle_error(e)
        app.notify("Сохранено")
        app.go("list")


class ArtFencingApp(App):
    title = "Арт-Фехтование"
    weapons = WEAPONS
    weapon_filter = ["Все"] + WEAPONS

    def build(self):
        Window.clearcolor = (0.08, 0.08, 0.11, 1)
        self.api = ApiClient(os.path.join(self.user_data_dir, "art_fencing.db"))
        Builder.load_file(os.path.join(os.path.dirname(__file__), "artfencing.kv"))
        self.sm = ScreenManager()
        for cls, name in [(LoginScreen, "login"), (RegisterScreen, "register"),
                          (HomeScreen, "home"), (ListScreen, "list"),
                          (DetailScreen, "detail"), (FormScreen, "form")]:
            self.sm.add_widget(cls(name=name))
        return self.sm

    # --- навигация ---
    def go(self, name):
        self.sm.current = name

    def open_detail(self, fighter_id):
        self.sm.get_screen("detail").fighter_id = fighter_id
        self.go("detail")

    def open_form(self, fighter_id):
        self.sm.get_screen("form").fighter_id = fighter_id
        self.go("form")

    def logout(self):
        self.api.logout()
        self.notify("Вы вышли из аккаунта")
        self.go("login")

    # --- сообщения ---
    def notify(self, text, error=False):
        color = (0.55, 0.12, 0.14, 1) if error else (0.13, 0.45, 0.25, 1)
        popup = Popup(title="Ошибка" if error else "Готово", content=Label(text=text),
                      size_hint=(0.8, None), height=dp(150), background_color=color)
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2.2)

    def handle_error(self, err: ApiError):
        if err.status == 401 and self.api.token:  # токен просрочен
            self.api.logout()
            self.go("login")
            return self.notify("Сессия истекла, войдите снова", error=True)
        self.notify(err.message, error=True)

    # --- удаление с подтверждением ---
    def confirm_delete(self, fighter_id):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(Label(text="Удалить запись безвозвратно?"))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(44))
        popup = Popup(title="Подтверждение", content=box, size_hint=(0.85, None), height=dp(210))

        def do_delete(*_):
            popup.dismiss()
            try:
                self.api.delete_fighter(fighter_id)
            except ApiError as e:
                return self.handle_error(e)
            self.notify("Запись удалена")
            self.go("list")

        yes = Button(text="Удалить", background_normal="", background_color=(0.55, 0.1, 0.12, 1))
        no = Button(text="Отмена", background_normal="", background_color=(0.25, 0.25, 0.33, 1))
        yes.bind(on_release=do_delete)
        no.bind(on_release=popup.dismiss)
        row.add_widget(yes)
        row.add_widget(no)
        box.add_widget(row)
        popup.open()


if __name__ == "__main__":
    ArtFencingApp().run()
