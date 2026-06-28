import { Anchor, type AnchorProps } from '@mantine/core';
import type { ComponentPropsWithoutRef, MouseEvent, ReactNode } from 'react';

import { hrefForAppPath, navigateTo } from '../lib/navigation';

type RouterAnchorProps = AnchorProps &
  Omit<ComponentPropsWithoutRef<'a'>, keyof AnchorProps | 'href'> & {
    children: ReactNode;
    to: string;
  };

export function RouterAnchor({ children, to, onClick, ...props }: RouterAnchorProps) {
  return (
    <Anchor
      {...props}
      href={hrefForAppPath(to)}
      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
        onClick?.(event);
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.altKey || event.ctrlKey || event.shiftKey) {
          return;
        }
        event.preventDefault();
        navigateTo(to);
      }}
    >
      {children}
    </Anchor>
  );
}
