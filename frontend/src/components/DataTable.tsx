import {
  type ColumnDef,
  type Row,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { Badge, Group, ScrollArea, Table, Text, TextInput, UnstyledButton } from '@mantine/core';
import { useState } from 'react';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function globalFilterFn(row: Row<any>, _columnId: string, filterValue: string): boolean {
  const query = filterValue.toLowerCase().trim();
  if (!query) return true;
  return Object.values(row.original as Record<string, unknown>).some((val) =>
    String(val ?? '').toLowerCase().includes(query),
  );
}

type DataTableProps<TData> = {
  data: TData[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  columns: ColumnDef<TData, any>[];
  searchPlaceholder?: string;
  searchLabel?: string;
  miw?: number;
};

export function DataTable<TData>({ data, columns, searchPlaceholder = 'Search…', searchLabel = 'Search inventory', miw }: DataTableProps<TData>) {
  const [globalFilter, setGlobalFilter] = useState('');

  const table = useReactTable({
    data,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const rows = table.getRowModel().rows;

  return (
    <div>
      <Group justify="space-between" align="center" mb="sm">
        <TextInput
          label={searchLabel}
          placeholder={searchPlaceholder}
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.currentTarget.value)}
          size="sm"
          miw={240}
          style={{ flex: 1, maxWidth: 360 }}
        />
        <Badge variant="light" color="cyan">{rows.length} of {data.length}</Badge>
      </Group>

      <ScrollArea type="auto" offsetScrollbars>
        <Table striped highlightOnHover miw={miw}>
          <Table.Thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sorted = header.column.getIsSorted();
                  return (
                    <Table.Th
                      key={header.id}
                      aria-sort={canSort ? (sorted === 'asc' ? 'ascending' : sorted === 'desc' ? 'descending' : 'none') : undefined}
                    >
                      {canSort ? (
                        <UnstyledButton type="button" onClick={header.column.getToggleSortingHandler()} aria-label={`Sort by ${String(header.column.columnDef.header)}`}>
                          <Group gap={4} wrap="nowrap">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          <Text size="xs" c="dimmed" component="span">
                            {sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : '↕'}
                          </Text>
                          </Group>
                        </UnstyledButton>
                      ) : flexRender(header.column.columnDef.header, header.getContext())}
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {rows.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={columns.length}>
                  <Text c="dimmed" size="sm" ta="center" py="md">No results match your search.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              rows.map((row) => (
                <Table.Tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <Table.Td key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </ScrollArea>
    </div>
  );
}
