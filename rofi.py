import sys
import main as switcher

def main():
    if len(sys.argv) == 1:
        manager = switcher.Manager()
        for name in manager.themes.keys():
            print(name)
    elif len(sys.argv) == 2:
        manager = switcher.Manager()
        manager.select_theme(sys.argv[1])
        manager.apply()

if __name__ == "__main__":
    main()

