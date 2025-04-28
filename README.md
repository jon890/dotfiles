# my custom dotfiles

## manjaro linux

- arch linux 보다 어느정도 체크포인트를 가져가면서 업데이트하는 리눅스 배포판

## 설치할 것

- homebrew (macos package manager)
- amethyst (tiling window manager)
- warp (terminal, ai, rust-based terminal)
- obsidian (note)
- zsh (enhanced shell)
- zim (zsh configuration framework)
- asdf (package manager)

## 설정법

```zsh
mv .git .. # 깃 디렉토리를 사용자 폴더로 이동
rm -rf dotfiles # 깃 레포지터리 삭제
git fetch origin
git reset --hard origin/HEAD
```

- `.git` 폴더에 최신 REVISION이 있기 때문에 지워도 무방하다.
