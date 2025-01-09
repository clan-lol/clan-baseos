import { StepProps } from "./hardware-step";
import { Typography } from "@/src/components/Typography";
import { FieldLayout } from "@/src/Form/fields/layout";
import { InputLabel } from "@/src/components/inputBase";
import { Group, Section, SectionHeader } from "@/src/components/group";
import { AllStepsValues } from "../details";
import { Badge } from "@/src/components/badge";
import Icon from "@/src/components/icon";

export const SummaryStep = (props: StepProps<AllStepsValues>) => {
  const hwValues = () => props.initial?.["1"];
  const diskValues = () => props.initial?.["2"];
  return (
    <>
      <div class="max-h-[calc(100vh-20rem)] overflow-y-scroll">
        <div class="flex h-full flex-col gap-6 p-4">
          <Section>
            <Typography
              hierarchy="label"
              size="xs"
              weight="medium"
              class="uppercase"
            >
              Hardware Report
            </Typography>
            <Group>
              <FieldLayout
                label={<InputLabel>Detected</InputLabel>}
                field={
                  hwValues()?.report ? (
                    <Badge color="green" class="w-fit">
                      <Icon icon="Checkmark" color="inherit" />
                    </Badge>
                  ) : (
                    <Badge color="red" class="w-fit">
                      <Icon icon="Warning" color="inherit" />
                    </Badge>
                  )
                }
              ></FieldLayout>
              <FieldLayout
                label={<InputLabel>Target</InputLabel>}
                field={
                  <Typography hierarchy="body" size="xs" weight="bold">
                    {hwValues()?.target}
                  </Typography>
                }
              ></FieldLayout>
            </Group>
          </Section>
          <Section>
            <Typography
              hierarchy="label"
              size="xs"
              weight="medium"
              class="uppercase"
            >
              Disk Configuration
            </Typography>
            <Group>
              <FieldLayout
                label={<InputLabel>Disk Layout</InputLabel>}
                field={
                  <Typography hierarchy="body" size="xs" weight="bold">
                    {diskValues()?.schema}
                  </Typography>
                }
              ></FieldLayout>
              <hr class="h-px w-full border-none bg-acc-3"></hr>
              <FieldLayout
                label={<InputLabel>Main Disk</InputLabel>}
                field={
                  <Typography hierarchy="body" size="xs" weight="bold">
                    {diskValues()?.placeholders.mainDisk}
                  </Typography>
                }
              ></FieldLayout>
            </Group>
          </Section>
          <SectionHeader
            variant="danger"
            headline={
              <span>
                <Typography
                  hierarchy="body"
                  size="s"
                  weight="bold"
                  color="inherit"
                >
                  Setup your device.
                </Typography>
                <Typography
                  hierarchy="body"
                  size="s"
                  weight="medium"
                  color="inherit"
                >
                  This will erase the disk and bootstrap fresh.
                </Typography>
              </span>
            }
          />
        </div>
      </div>
      {props.footer}
    </>
  );
};
