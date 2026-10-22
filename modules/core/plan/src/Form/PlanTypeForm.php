<?php

declare(strict_types=1);

namespace Drupal\plan\Form;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Entity\EntityForm;
use Drupal\Core\Form\FormStateInterface;
use Drupal\state_machine\WorkflowManagerInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Form controller for plan type entities.
 *
 * @package Drupal\plan\Form
 */
class PlanTypeForm extends EntityForm {

  use AutowireTrait;

  /**
   * The plan type entity.
   *
   * @var \Drupal\plan\Entity\PlanTypeInterface
   */
  protected $entity;

  public function __construct(
    #[Autowire(service: 'plugin.manager.workflow')]
    protected WorkflowManagerInterface $workflowManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function form(array $form, FormStateInterface $form_state) {
    $form = parent::form($form, $form_state);
    $plan_type = $this->entity;

    $form['label'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Label'),
      '#maxlength' => 255,
      '#default_value' => $plan_type->label(),
      '#description' => $this->t('Label for the plan type.'),
      '#required' => TRUE,
    ];

    $form['id'] = [
      '#type' => 'machine_name',
      '#default_value' => $plan_type->id(),
      '#machine_name' => [
        'exists' => '\Drupal\plan\Entity\PlanType::load',
      ],
      '#disabled' => !$plan_type->isNew(),
    ];

    $form['description'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Description'),
      '#default_value' => $plan_type->getDescription(),
    ];

    $form['workflow'] = [
      '#type' => 'select',
      '#title' => $this->t('Workflow'),
      '#options' => $this->workflowManager->getGroupedLabels('plan'),
      '#default_value' => $plan_type->getWorkflowId(),
      '#description' => $this->t('Used by all plans of this type.'),
    ];

    $form['new_revision'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Create new revision'),
      '#default_value' => $plan_type->shouldCreateNewRevision(),
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function save(array $form, FormStateInterface $form_state) {
    $plan_type = $this->entity;
    $status = $plan_type->save();

    switch ($status) {
      case SAVED_NEW:
        $this->messenger()->addMessage($this->t('Created the %label plan type.', [
          '%label' => $plan_type->label(),
        ]));
        break;

      default:
        $this->messenger()->addMessage($this->t('Saved the %label plan type.', [
          '%label' => $plan_type->label(),
        ]));
    }
    $form_state->setRedirectUrl($plan_type->toUrl('collection'));

    return $status;
  }

}
